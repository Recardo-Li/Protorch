import streamlit as st
import sys

ROOT_DIR = str(__file__).rsplit("/", 3)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from streamlit_demo.modules.login import st_login

st.set_page_config(
    page_title="ProtAgent - Login",
    page_icon="🔒",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st_login()
