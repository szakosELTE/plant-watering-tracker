import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta, time
from streamlit_cookies_manager import EncryptedCookieManager
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Cookie manager inicializálása
cookies = EncryptedCookieManager(prefix="planttracker_", password="egy-erős-es-minimum-16-karakteres-jelszo")
if not cookies.ready():
    st.stop()

# SMTP email küldő függvény
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

# ----- SESSION KEZELÉS ÉS ADATBÁZIS FUNKCIÓK -----
def init_session_from_cookies():
    if cookies.get("authenticated") == "true":
        st.session_state["authenticated"] = True
        st.session_state["username"] = cookies.get("username")
    else:
        st.session_state["authenticated"] = False
        st.session_state["username"] = None

def login_user(username):
    st.session_state["authenticated"] = True
    st.session_state["username"] = username
    cookies["authenticated"] = "true"
    cookies["username"] = username
    cookies.save()

def logout_user():
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    if "authenticated" in cookies:
        del cookies["authenticated"]
    if "username" in cookies:
        del cookies["username"]
    cookies.save()

def init_session():
    if "authenticated" not in st.session_state or "username" not in st.session_state:
        init_session_from_cookies()
    create_users_table()

# ---------- ADATBÁZIS USER FUNKCIÓK ----------
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

def add_user(username, password, email=None):
    hashed_pw = hash_password(password)
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", (username, hashed_pw, email))
    conn.commit()
    conn.close()

def get_user(username):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    conn.close()
    return user

def get_all_user_emails():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE email IS NOT NULL AND email != ''")
    emails = [row[0] for row in cur.fetchall()]
    conn.close()
    return emails

# ---------- SEGÉDFÜGGVÉNYEK ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(input_password, stored_password):
    return hash_password(input_password) == stored_password

def watered_today(plant):
    last_watered_str = plant[4]  # last_watered mező
    if not last_watered_str:
        return False
    last_watered_date = datetime.strptime(last_watered_str, "%Y-%m-%d").date()
    return last_watered_date == datetime.now().date()

def send_watering_reminder_if_needed():
    now = datetime.now()
    if now.time() < time(18, 0):  # 18:00 előtt ne küldjünk
        return

    from database import get_all_plants

    plants = get_all_plants()

    # Öntözendő növények kiszűrése az aktuális dátumhoz képest
    plants_due_today = []
    for p in plants:
        last_watered_str = p[4]
        freq = p[3]
        if not last_watered_str:
            plants_due_today.append(p)
            continue
        last_watered_date = datetime.strptime(last_watered_str, "%Y-%m-%d").date()
        next_due_date = last_watered_date + timedelta(days=freq)
        if datetime.now().date() >= next_due_date:
            plants_due_today.append(p)

    # Olyanok, amiket ma még nem öntöztek meg
    not_watered_yet = [p for p in plants_due_today if not watered_today(p)]

    if not not_watered_yet:
        return

    emails = get_all_user_emails()
    if not emails:
        return

    body_lines = ["Ma még öntözni kell ezeken a növényeken:"]
    for p in not_watered_yet:
        body_lines.append(f"- {p[2]} (tulajdonos: {p[1]})")
    body = "\n".join(body_lines)
    subject = "Növény öntözési emlékeztető"

    sender_email = st.secrets["email"]["address"]
    sender_password = st.secrets["email"]["password"]

    send_email(
        to_emails=emails,
        subject=subject,
        body=body,
        sender_email=sender_email,
        sender_password=sender_password
    )

# ---------- BEJELENTKEZÉS ÉS REGISZTRÁCIÓ ----------
def show_login():
    tabs = st.tabs(["Bejelentkezés", "Regisztráció"])

    with tabs[0]:
        st.subheader("Bejelentkezés")
        username = st.text_input("Felhasználónév", key="login_user")
        password = st.text_input("Jelszó", type="password", key="login_pass")
        if st.button("Bejelentkezés"):
            user = get_user(username)
            if user and verify_password(password, user[2]):
                login_user(username)
                st.success(f"Szia, {username}! Sikeresen bejelentkeztél.")
                st.rerun()
            else:
                st.error("Érvénytelen felhasználónév vagy jelszó.")

    with tabs[1]:
        st.subheader("Regisztráció")
        new_user = st.text_input("Új felhasználónév", key="reg_user")
        new_pass = st.text_input("Új jelszó", type="password", key="reg_pass")
        new_email = st.text_input("Email cím", key="reg_email")
        if st.button("Regisztráció"):
            if get_user(new_user):
                st.warning("A felhasználónév már foglalt.")
            elif new_user and new_pass and new_email:
                add_user(new_user, new_pass, new_email)
                st.success("Sikeres regisztráció! Kérlek, jelentkezz be.")
            else:
                st.warning("Kérlek, töltsd ki az összes mezőt.")

def show_dashboard():
    from database import (
        create_plant_table, create_watering_logs_table,
        add_plant, get_all_plants,
        delete_plant, update_last_watered_and_log,
        get_plants_due_today, get_last_watering_info,
        get_user_email, delete_user_and_plants
    )
    import smtplib
    from email.mime.text import MIMEText

    create_plant_table()
    create_watering_logs_table()

    send_watering_reminder_if_needed()  # az email értesítés ellenőrzése

    st.success(f"Bejelentkezve: {st.session_state['username']}")
    st.header("Növénykezelő Felület")

    username = st.session_state["username"]
    user_email = get_user_email(username)
    sender_email = st.secrets["email"]["address"]
    sender_password = st.secrets["email"]["password"]

    def send_test_email():
        if not user_email:
            st.error("Az email címed nincs megadva, nem lehet teszt emailt küldeni.")
            return
        msg = MIMEText("Ez egy teszt email a Plant Watering Tracker appból.")
        msg['Subject'] = "Teszt Email"
        msg['From'] = sender_email
        msg['To'] = user_email
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
            st.success(f"Teszt email elküldve a(z) {user_email} címre.")
        except Exception as e:
            st.error(f"Hiba történt a teszt email küldésekor: {e}")

    if st.button("Teszt Email küldése"):
        send_test_email()

    st.markdown("---")
    st.subheader("Profil törlése")
    confirm_del = st.checkbox("Biztos vagyok benne, hogy törlöm a profilomat és az összes növényemet")
    if st.button("Fiókom törlése és kijelentkezés"):
        if confirm_del:
            delete_user_and_plants(username)
            logout_user()
            st.success("Sikeresen töröltük a profilod és kijelentkeztünk.")
            st.rerun()
        else:
            st.warning("Kérlek, erősítsd meg a profil törlését az előző jelölőnégyzettel!")

    # Öntözendő növények listája
    due_today_plants = get_plants_due_today(username)
    if due_today_plants:
        st.markdown("### ⚠️ Ma öntözendő növényeid:")
        for plant in due_today_plants:
            st.write(f"🌿 **{plant[2]}** (utoljára öntözve: {plant[4]})")
        st.markdown("---")
    else:
        st.info("Ma egy növényt sem kell öntözni. Szép napot! 🌞")

    with st.expander("Új növény hozzáadása"):
        with st.form("add_plant_form"):
            plant_name = st.text_input("Növény neve", key="new_plant_name")
            frequency = st.number_input("Öntözés gyakorisága (napokban)", min_value=1, max_value=365, step=1, key="new_plant_freq")
            submitted = st.form_submit_button("Növény hozzáadása")
            if submitted:
                if plant_name.strip() == "":
                    st.warning("Kérlek, add meg a növény nevét.")
                else:
                    add_plant(username, plant_name.strip(), int(frequency))
                    st.success(f"Hozzáadva: {plant_name.strip()}")
                    st.rerun()

    plants = get_all_plants()
    if not plants:
        st.info("Nincs még növény a rendszerben.")
        return

    plants_list = [
        {
            "id": p[0],
            "username": p[1],
            "name": p[2],
            "frequency_days": p[3],
            "last_watered": p[4],
        }
        for p in plants
    ]

    st.subheader("Növényeid")
    for plant in plants_list:
        plant_id = plant["id"]
        due = plant_id in [p[0] for p in get_plants_due_today(username)]
        last_watering = get_last_watering_info(plant_id)
        if last_watering:
            watered_by, watered_at = last_watering
        else:
            watered_by, watered_at = "Ismeretlen", "Nincs adat"

        cols = st.columns([3,2,2,2,2,2])
        with cols[0]:
            st.write(f"🌿 **{plant['name']}**")
        with cols[1]:
            st.write(f"Minden {plant['frequency_days']} nap")
        with cols[2]:
            st.write(f"Utolsó öntözés: {plant['last_watered']}")
        with cols[3]:
            if due:
                st.markdown("**⚠️ Öntözni kell!**")
            else:
                st.markdown("✅ Rendben van")
        with cols[4]:
            st.write(f"Utolsó öntöző: **{watered_by}**")
        with cols[5]:
            if st.button("🗑️", key=f"del_{plant_id}"):
                delete_plant(plant_id, None)
                st.success(f"Törölve: {plant['name']}")
                st.rerun()
            if st.button("💧", key=f"water_{plant_id}"):
                update_last_watered_and_log(plant_id, username)
                st.success(f"Öntözve: {plant['name']}")
                st.rerun()

    if st.button("Kijelentkezés"):
        logout_user()
        st.rerun()