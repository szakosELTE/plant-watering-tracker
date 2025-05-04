import sqlite3
import smtplib
from datetime import datetime, timedelta, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME_PLANTS = os.path.join(BASE_DIR, "plants.db")
DB_NAME_USERS = os.path.join(BASE_DIR, "users.db")

def create_users_table():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT
        )
    """)
    conn.commit()
    conn.close()

def create_plants_table():
    conn = sqlite3.connect("plants.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS plants (
            id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            frequency_days INTEGER,
            last_watered TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_all_plants():
    conn = sqlite3.connect(DB_NAME_PLANTS)
    cur = conn.cursor()
    cur.execute("SELECT * FROM plants")
    plants = cur.fetchall()
    conn.close()
    return plants

def get_all_user_emails():
    conn = sqlite3.connect(DB_NAME_USERS)
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE email IS NOT NULL AND email != ''")
    emails = [row[0] for row in cur.fetchall()]
    conn.close()
    return emails

def watered_today(plant):
    last_watered_str = plant[4]
    if not last_watered_str:
        return False
    last_watered_date = datetime.strptime(last_watered_str, "%Y-%m-%d").date()
    return last_watered_date == datetime.now().date()

def send_email(to_emails, subject, body, sender_email, sender_password,
               smtp_server="smtp.gmail.com", smtp_port=465):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(to_emails)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_emails, msg.as_string())

def main():
    create_users_table()
    create_plants_table()
    now = datetime.now()
    if now.time() < time(18, 0):
        print("Még nincs itt az idő az email küldéshez.")
        return

    plants = get_all_plants()
    due_plants = []
    for p in plants:
        last_watered = p[4]
        freq = p[3]
        if not last_watered:
            due_plants.append(p)
            continue
        last_date = datetime.strptime(last_watered, "%Y-%m-%d")
        if now.date() >= (last_date + timedelta(days=freq)).date():
            due_plants.append(p)

    not_watered = [p for p in due_plants if not watered_today(p)]

    if not not_watered:
        print("Nincs ma öntözendő növény vagy már mind meg lett öntözve.")
        return

    emails = get_all_user_emails()
    if not emails:
        print("Nincsenek felhasználói email címek.")
        return

    body = "Ma még öntözni kell ezeken a növényeken:\n" + \
           "\n".join([f"- {p[2]} (tulajdonos: {p[1]})" for p in not_watered])
    subject = "Növény öntözési emlékeztető"

    sender_email = os.environ.get("EMAIL_ADDRESS")
    sender_password = os.environ.get("EMAIL_PASSWORD")

    if not sender_email or not sender_password:
        print("Hiányzó SMTP hitelesítő adatok az EMAIL_ADDRESS vagy EMAIL_PASSWORD környezeti változóban.")
        return

    send_email(emails, subject, body, sender_email, sender_password)
    print("Értesítő email elküldve.")

if __name__ == "__main__":
    main()