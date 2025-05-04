import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
from streamlit_cookies_manager import EncryptedCookieManager

# Cookie manager inicializálása (válassz erős jelszót, itt csak példa)
cookies = EncryptedCookieManager(prefix="planttracker_", password="egy-erős-es-minimum-16-karakteres-jelszo")

if not cookies.ready():
    # Várunk, amíg a cookie manager beállításra kerül
    st.stop()

# ---------- ADATBÁZIS FUNKCIÓK ----------
def create_users_table():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(username, password):
    hashed_pw = hash_password(password)
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
    conn.commit()
    conn.close()

def get_user(username):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    conn.close()
    return user

# ---------- SEGÉDFÜGGVÉNYEK ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(input_password, stored_password):
    return hash_password(input_password) == stored_password

# ---------- COOKIE-VAL KOMPATIBILIS SESSION KEZELÉS ----------

def init_session_from_cookies():
    # Beállítjuk a session_state-et cookie alapján, ha van bejelentkezve felhasználó
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
    cookies["authenticated"] = None
    cookies["username"] = None
    cookies.save()

def init_session():
    if "authenticated" not in st.session_state or "username" not in st.session_state:
        init_session_from_cookies()
    create_users_table()

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
                login_user(username)   # itt már a cookie-ba is mentünk
                st.success(f"Szia, {username}! Sikeresen bejelentkeztél.")
                st.rerun()
            else:
                st.error("Érvénytelen felhasználónév vagy jelszó.")

    with tabs[1]:
        st.subheader("Regisztráció")
        new_user = st.text_input("Új felhasználónév", key="reg_user")
        new_pass = st.text_input("Új jelszó", type="password", key="reg_pass")
        if st.button("Regisztráció"):
            if get_user(new_user):
                st.warning("A felhasználónév már foglalt.")
            elif new_user and new_pass:
                add_user(new_user, new_pass)
                st.success("Sikeres regisztráció! Kérlek, jelentkezz be.")
            else:
                st.warning("Kérlek, adj meg felhasználónevet és jelszót.")

# ---------- FŐOLDAL, A KERTI NÖVÉNYEK KEZELÉSE ----------
def show_dashboard():
    from database import (
        create_plant_table, add_plant, get_user_plants,
        delete_plant, update_last_watered, get_plants_due_today
    )
    create_plant_table()

    st.success(f"Bejelentkezve: {st.session_state['username']}")
    st.header("Növénykezelő Felület")

    username = st.session_state["username"]

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

    plants = get_user_plants(username)
    if not plants:
        st.info("Még nincs hozzáadott növényed. Használd a fenti űrlapot!")
        return
    
    plants_list = [
        {
            "id": p[0],
            "name": p[2],
            "frequency_days": p[3],
            "last_watered": p[4],
        }
        for p in plants
    ]

    due_plants = get_plants_due_today(username)
    due_ids = [p[0] for p in due_plants]

    st.subheader("Növényeid")
    for plant in plants_list:
        plant_id = plant["id"]
        due = plant_id in due_ids

        cols = st.columns([4, 2, 2, 2, 1])
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
            if st.button("🗑️", key=f"del_{plant_id}"):
                delete_plant(plant_id, username)
                st.success(f"Törölve: {plant['name']}")
                st.rerun()
            if st.button("💧", key=f"water_{plant_id}"):
                update_last_watered(plant_id, username)
                st.success(f"Öntözve: {plant['name']}")
                st.rerun()

    if st.button("Kijelentkezés"):
        logout_user()
        st.rerun()