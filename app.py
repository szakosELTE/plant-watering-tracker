import streamlit as st
from app_logic import init_session, show_login, show_dashboard

# A set_page_config-nek EZ AZ ELSŐ Streamlit hívásnak kell lennie
st.set_page_config(page_title="Plant Watering Tracker", layout="centered")

# Session inicializálása
init_session()

st.title("🌱 Plant Watering Tracker")

if not st.session_state.get("authenticated"):
    show_login()
else:
    show_dashboard()