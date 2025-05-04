# database.py

import sqlite3
from datetime import datetime, timedelta

DB_NAME = "plants.db"

# ---------- DB SETUP ----------

def create_plant_table():
    conn = sqlite3.connect(DB_NAME)
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

#---------- CRUD FUNCTIONS ----------

def add_plant(username, name, frequency_days):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO plants (username, name, frequency_days, last_watered)
        VALUES (?, ?, ?, ?)
    """, (username, name, frequency_days, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()


def get_user_plants(username):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM plants WHERE username = ?", (username,))
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_plant(plant_id, username):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM plants WHERE id = ? AND username = ?", (plant_id, username))
    conn.commit()
    conn.close()

def update_last_watered(plant_id, username):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        UPDATE plants SET last_watered = ?
        WHERE id = ? AND username = ?
    """, (datetime.now().strftime("%Y-%m-%d"), plant_id, username))
    conn.commit()
    conn.close()

# ---------- DUE TODAY ----------

def get_plants_due_today(username):
    plants = get_user_plants(username)
    due_today = []

    for plant in plants:
        _, _, name, freq, last_watered = plant
        last_date = datetime.strptime(last_watered, "%Y-%m-%d")
        next_due = last_date + timedelta(days=freq)
        if datetime.now().date() >= next_due.date():
            due_today.append(plant)

    return due_today
