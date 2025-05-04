# app_logic.py

import streamlit as st
import sqlite3
import hashlib
from datetime import datetime


# újraindítás funkció - szükség esetén ide beilleszthető

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

# ---------- MUNKAFOLYAM ÁLLAPOT (SESSION) KEZELÉS ----------

def init_session():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = None
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
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
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
    import streamlit as st

    create_plant_table()  # biztosítjuk, hogy legyen növény tábla

    st.success(f"Bejelentkezve: {st.session_state['username']}")
    st.header("Növénykezelő Felület")

    username = st.session_state["username"]

    # --- NAPI EMLÉKEZTETŐ ---
    due_today_plants = get_plants_due_today(username)
    #st.write("DEBUG: Ma öntözendő növények:", due_today_plants)
    if due_today_plants:
        st.markdown("### ⚠️ Ma öntözendő növényeid:")
        for plant in due_today_plants:
            # plant = (id, username, name, frequency_days, last_watered)
            st.write(f"🌿 **{plant[2]}** (utoljára öntözve: {plant[4]})")
        st.markdown("---")  # elválasztó vonal
    else:
        st.info("Ma egy növényt sem kell öntözni. Szép napot! 🌞")

    # --- Növény hozzáadása űrlap ---
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
                    st.rerun()  # frissítés a hozzáadás után

    # --- Növények listázása ---
    plants = get_user_plants(username)
    if not plants:
        st.info("Még nincs hozzáadott növényed. Használd a fenti űrlapot!")
        return
    
    # Átalakítás könnyebb kezeléshez
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

        # Műveleti gombok (törlés, öntözés jelölése)
        with cols[4]:
            if st.button("🗑️", key=f"del_{plant_id}"):
                delete_plant(plant_id, username)
                st.success(f"Törölve: {plant['name']}")
                st.rerun()

            if st.button("💧", key=f"water_{plant_id}"):
                update_last_watered(plant_id, username)
                st.success(f"Öntözve: {plant['name']}")
                st.rerun()

    # --- Kijelentkezés ---
    if st.button("Kijelentkezés"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = None
        st.rerun()