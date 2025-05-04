# app_logic.py

import streamlit as st
import sqlite3
import hashlib
from datetime import datetime


# def rerun():
#     params = st.query_params
#     params["_rerun"] = [str(int(datetime.now().timestamp()))]
#     st.query_params = params
#     st.stop()

# ---------- DATABASE FUNCTIONS ----------

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

# ---------- UTILITIES ----------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(input_password, stored_password):
    return hash_password(input_password) == stored_password

# ---------- SESSION INIT ----------

def init_session():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = None
    create_users_table()

# ---------- LOGIN / REGISTRATION ----------

def show_login():
    tabs = st.tabs(["Login", "Register"])

    with tabs[0]:
        st.subheader("Login")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            user = get_user(username)
            if user and verify_password(password, user[2]):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.success(f"Welcome back, {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tabs[1]:
        st.subheader("Register")
        new_user = st.text_input("New Username", key="reg_user")
        new_pass = st.text_input("New Password", type="password", key="reg_pass")
        if st.button("Register"):
            if get_user(new_user):
                st.warning("Username already taken.")
            elif new_user and new_pass:
                add_user(new_user, new_pass)
                st.success("User registered. Please log in.")
            else:
                st.warning("Please enter a username and password.")

# ---------- DASHBOARD ----------

def show_dashboard():
    from database import (
        create_plant_table, add_plant, get_user_plants,
        delete_plant, update_last_watered, get_plants_due_today
    )
    import streamlit as st

    create_plant_table()  # ensure plants table exists

    st.success(f"Logged in as {st.session_state['username']}")
    st.header("Your Plant Dashboard")

    username = st.session_state["username"]

    # --- Form to add plant ---
    with st.expander("Add a New Plant"):
        with st.form("add_plant_form"):
            plant_name = st.text_input("Plant Name", key="new_plant_name")
            frequency = st.number_input("Watering Frequency (days)", min_value=1, max_value=365, step=1, key="new_plant_freq")
            submitted = st.form_submit_button("Add Plant")

            if submitted:
                if plant_name.strip() == "":
                    st.warning("Please enter a plant name.")
                else:
                    add_plant(username, plant_name.strip(), int(frequency))
                    st.success(f"Added plant: {plant_name.strip()}")
                    st.rerun()  # refresh after submission

    # --- List user plants ---
    plants = get_user_plants(username)
    if not plants:
        st.info("You have no plants yet. Add one above!")
        return
    
    # Convert to a list of dicts for easier handling
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

    st.subheader("Your Plants")
    for plant in plants_list:
        plant_id = plant["id"]
        due = plant_id in due_ids

        cols = st.columns([4, 2, 2, 2, 1])
        with cols[0]:
            st.write(f"🌿 **{plant['name']}**")
        with cols[1]:
            st.write(f"Every {plant['frequency_days']} day(s)")
        with cols[2]:
            st.write(f"Last watered: {plant['last_watered']}")
        with cols[3]:
            if due:
                st.markdown("**⚠️ Needs water!**")
            else:
                st.markdown("✅ Up to date")

        # Buttons for actions (delete, mark watered)
        with cols[4]:
            if st.button("🗑️", key=f"del_{plant_id}"):
                delete_plant(plant_id, username)
                st.success(f"Deleted {plant['name']}")
                st.rerun()

            if st.button("💧", key=f"water_{plant_id}"):
                update_last_watered(plant_id, username)
                st.success(f"Marked {plant['name']} as watered.")
                st.rerun()

    # --- Logout ---
    if st.button("Log out"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = None
        st.rerun()