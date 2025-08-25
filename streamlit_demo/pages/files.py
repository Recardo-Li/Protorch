import streamlit as st
import sys
import os

ROOT_DIR = str(__file__).rsplit("/", 3)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from streamlit_demo.components.file_preview import dialog_file_preview
from streamlit_demo.modules.file_browser import st_file_manager

st.set_page_config(
    page_title="ProtAgent - Files",
    page_icon="📁",
    layout="centered",
    initial_sidebar_state="collapsed",
)

if not st.session_state.get("authentication_status"):
    st.switch_page("pages/login.py")

st.page_link("pages/chat.py", label="Back to chat", icon=":material/arrow_back:")  # Add a back button to the chat page

st.title("File Mangaer")

st_file_manager(st.session_state.out_dir)
