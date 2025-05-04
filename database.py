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

def create_watering_logs_table():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS watering_logs (
            id INTEGER PRIMARY KEY,
            plant_id INTEGER,
            watered_by TEXT,
            watered_at TEXT,
            FOREIGN KEY (plant_id) REFERENCES plants(id)
        )
    """)
    conn.commit()
    conn.close()

# ---------- CRUD FUNCTIONS ----------

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

def get_all_plants():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM plants")
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_plant(plant_id, username=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    if username is None:
        cur.execute("DELETE FROM plants WHERE id = ?", (plant_id,))
    else:
        cur.execute("DELETE FROM plants WHERE id = ? AND username = ?", (plant_id, username))
    conn.commit()
    conn.close()

def update_last_watered(plant_id, username=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        UPDATE plants SET last_watered = ?
        WHERE id = ?
    """, (datetime.now().strftime("%Y-%m-%d"), plant_id))
    conn.commit()
    conn.close()

def add_watering_log(plant_id, watered_by):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    watered_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO watering_logs (plant_id, watered_by, watered_at)
        VALUES (?, ?, ?)
    """, (plant_id, watered_by, watered_at))
    conn.commit()
    conn.close()

def update_last_watered_and_log(plant_id, watered_by):
    update_last_watered(plant_id)
    add_watering_log(plant_id, watered_by)

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

def get_last_watering_info(plant_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT watered_by, watered_at FROM watering_logs
        WHERE plant_id = ?
        ORDER BY watered_at DESC
        LIMIT 1
    """, (plant_id,))
    row = cur.fetchone()
    conn.close()
    return row  # (watered_by, watered_at) vagy None

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

def get_all_user_emails():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE email IS NOT NULL AND email != ''")
    emails = [row[0] for row in cur.fetchall()]
    conn.close()
    return emails

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