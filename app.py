# app.py (main Streamlit app)
import streamlit as st
from app_logic import init_session, show_login, show_dashboard

# Initialize session state
init_session()

st.set_page_config(page_title="Plant Watering Tracker", layout="centered")
st.title("🌱 Plant Watering Tracker")

# Authenticated routing
if not st.session_state.get("authenticated"):
    show_login()
else:
    show_dashboard()
