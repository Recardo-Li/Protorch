import streamlit as st
import sys

ROOT_DIR = str(__file__).rsplit("/", 3)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from streamlit_demo.modules.new_tool import add_new_tool
from streamlit_demo.modules.tool_viewer import show_available_tools

st.set_page_config(
    page_title="ProtAgent - Tools",
    page_icon="🛠️",
    layout="centered",
    initial_sidebar_state="collapsed",
)


if not st.session_state.get("authentication_status"):
    st.switch_page("pages/login.py")


st.page_link("pages/chat.py", label="Back to chat", icon=":material/arrow_back:")  # Add a back button to the chat page


st.title("Available Tools")
st.markdown(
    """
    Here are the available tools you can use. Click on each tool to see its details.
    """
)
with st.container(height=500):
    show_available_tools()

st.write("*Advanced Feature (Under maintainance):")
if st.button("Add New Tool"):
    add_new_tool()

if st.session_state.get("added_tool"):
    st.success(f"Tool {st.session_state.added_tool['name']} added successfully!")
    
