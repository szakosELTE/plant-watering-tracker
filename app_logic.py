import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
from streamlit_cookies_manager import EncryptedCookieManager

# Cookie manager inicializálása
cookies = EncryptedCookieManager(prefix="planttracker_", password="egy-erős-es-minimum-16-karakteres-jelszo")
if not cookies.ready():
    st.stop()

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
    cookies["authenticated"] = None
    cookies["username"] = None
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
        create_plant_table, create_watering_logs_table,
        add_plant, get_all_plants,
        delete_plant, update_last_watered_and_log,
        get_plants_due_today, get_last_watering_info
    )
    create_plant_table()
    create_watering_logs_table()

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

    # Minden növény listázása — Mindenki látja az összes növényt
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

    # Megjelenítés
    st.subheader("Növényeid")
    for plant in plants_list:
        plant_id = plant["id"]
        due = plant_id in [p[0] for p in get_plants_due_today(username)]
        last_watering = get_last_watering_info(plant_id)
        if last_watering:
            watered_by, watered_at = last_watering
        else:
            watered_by, watered_at = "Ismeretlen", "Nincs adat"

        cols = st.columns([3, 2, 2, 2, 2, 2])
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
            if plant["username"] == username:
                # Csak a növény létrehozója törölhet
                if st.button("🗑️", key=f"del_{plant_id}"):
                    delete_plant(plant_id, username)
                    st.success(f"Törölve: {plant['name']}")
                    st.rerun()
                if st.button("💧", key=f"water_{plant_id}"):
                    update_last_watered_and_log(plant_id, username)
                    st.success(f"Öntözve: {plant['name']}")
                    st.rerun()
            else:
                # Mások növényeihez nem engedélyezünk szerkesztést
                st.write("")

    if st.button("Kijelentkezés"):
        logout_user()
        st.rerun()