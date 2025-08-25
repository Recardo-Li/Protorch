import sys
import time
import os

# Add ROOT directory to sys.path
ROOT_DIR = str(__file__).rsplit("/", 3)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import base64
import streamlit as st
import streamlit_nested_layout

from streamlit_demo.modules.chatbot import st_chatbot
from streamlit_demo.modules.chat_history import st_chat_history, st_new_chat

def get_base64_of_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')


st.set_page_config(
    page_title="ProtAgent",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)



# Ask users to login
if not st.session_state.get("authentication_status"):
    st.switch_page("pages/login.py")

else:
    # Hide the animation of a running man on top of the Streamlit app.
    # hide_running_man()

    image_path = f"{ROOT_DIR}/img/logo.svg"
    base64_image = get_base64_of_image(image_path)
    st.logo(f"data:image/svg+xml;base64,{base64_image}", size="large", icon_image=f"data:image/svg+xml;base64,{base64_image}")
    
    with st.sidebar:
        # if st.button(label="New conversation",key="new_conversation_btn",icon=":material/add:", disabled=(st.session_state.get("is_chatting", False) or st.session_state.get("messages", []) == [])):
        #     st_new_chat()
        # st_profile()
        # st_tool_viewer()
        st_chat_history()
        # st_file_browser(st.session_state.out_dir)
    
    # with stylable_container(
    #     key="profile",
    #     css_styles=["""
    #     div{
    #         float: left;
    #     }""",
    #     """
    #     div{
    #         float: right;
    #     }
    #     """]
    # ):
    col1, col2, col3, col4, col5 = st.columns([6, 1, 1, 1, 1], vertical_alignment="center")
    with col1:     
        on = st.toggle("Manually confirm tool call", disabled=st.session_state.get("is_chatting", False))
        st.session_state.tool_call_confirmation = on
        if on:
            st.markdown("(The agent will wait for your confirmation before calling a tool)")
    with col2:
        st.page_link("pages/files.py", label="Files", icon="📁")
    with col3:
        st.page_link("pages/tools.py", label="ToolSet", icon="🛠️")
    with col4:
        st.page_link("pages/workflow.py", label="Workflow", icon="🔄")
    with col5:
        st.page_link("pages/user.py", label="Profile", icon="👤")
    
    
    st_chatbot()
    # from streamlit_demo.components.tool_form import st_tool_form
    # st_tool_form("tmalign", agent_kwargs={})

    # import streamlit as st
    #
    # prompt = st.chat_input(
    #     "Say something and/or attach an image",
    #     accept_file='multiple',
    # )
    #
    # st.write(prompt)
