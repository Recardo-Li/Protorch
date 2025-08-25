import streamlit as st
import sys

ROOT_DIR = str(__file__).rsplit("/", 3)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from streamlit_demo.modules.login import reset_password

st.set_page_config(
    page_title="ProtAgent - Profile",
    page_icon="👤",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.page_link("pages/chat.py", label="Back to chat", icon=":material/arrow_back:")  # Add a back button to the chat page

if st.session_state.get("authentication_status") is None:
    st.switch_page("pages/login.py")
    
else:
    st.markdown(f"## Welcome *{st.session_state.name}*")
    st.session_state.authenticator.logout(key="logout_user_page")
    if st.button("Reset password"):
        reset_password()

        

