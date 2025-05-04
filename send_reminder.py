import sqlite3
import smtplib
from datetime import datetime, timedelta, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

DB_NAME_PLANTS = "plants.db"
DB_NAME_USERS = "users.db"

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