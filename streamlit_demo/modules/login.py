import streamlit_authenticator as stauth
import streamlit as st
import os
import yaml
import sys

ROOT_DIR = str(__file__).rsplit("/", 3)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from streamlit_demo.components.init_agent import init_tool_manager


from yaml.loader import SafeLoader


def initialize_session_state():
    # Set output directory
    st.session_state.out_dir = f"{ROOT_DIR}/output/{st.session_state.username}"
    # st.session_state.out_dir = f"/home/public/ProtAgent/examples"
    st.session_state.chat_history_dir = f"{st.session_state.out_dir}/chat_history"
    st.session_state.workflow_dir = f"{st.session_state.out_dir}/workflows"
    # Public shared workflows directory
    st.session_state.public_out_dir = f"{ROOT_DIR}/output/public"
    st.session_state.public_workflow_dir = f"{st.session_state.public_out_dir}/workflows"
    os.makedirs(st.session_state.out_dir, exist_ok=True)
    os.makedirs(st.session_state.chat_history_dir, exist_ok=True)
    os.makedirs(st.session_state.public_workflow_dir, exist_ok=True)

    # Initialize the tool manager
    st.session_state.tool_manager = init_tool_manager()


def st_login():
    if not st.session_state.get('authentication_status'):
        login_tab, register_tab = st.tabs(["Login", "Register"])
        
        with login_tab:
            login()
        
        with register_tab:
            register()
    
    else:
        
        initialize_session_state()
        st.switch_page("pages/chat.py")


def login():
    BASE_DIR = os.path.dirname(__file__)
    config_path = f"{BASE_DIR}/../authentication.yaml"
    
    # Load config
    with open(config_path) as file:
        config = yaml.load(file, Loader=SafeLoader)
    
    # Pre-hashing all plain text passwords once
    # stauth.Hasher.hash_passwords(config['credentials'])
    
    st.session_state.authenticator = stauth.Authenticate(
        config_path,
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    
    try:
        st.session_state.authenticator.login()
        
        if st.session_state.get('authentication_status') is False:
            st.error('Username/password is incorrect')
        
        elif st.session_state.get('authentication_status') is None:
            st.warning('Please enter your username and password')

    except Exception as e:
        st.error(e)


def register():
    try:
        email, login_name, real_name = st.session_state.authenticator.register_user(captcha=False, password_hint=False)
        st.success('User registered successfully')
    except Exception as e:
        st.error(e)


@st.dialog("Reset password")
def reset_password():
    try:
        fields = {
            "Form name": "",
            'Current password': 'Current password',
            'New password': 'New password',
            'Repeat password': 'Repeat password',
            'Reset': 'Reset',
        }
        if st.session_state.authenticator.reset_password(st.session_state.get('username'), fields=fields):
            st.success('Password modified successfully')
    except Exception as e:
        st.error(e)
        

def st_profile():
    st.markdown(f"## Welcome *{st.session_state.name}*")
    st.session_state.authenticator.logout(key="logout_user_page")
    if st.button("Reset password"):
        reset_password()
    if st.button("Back to chat"):
        st.switch_page("pages/chat.py")
        