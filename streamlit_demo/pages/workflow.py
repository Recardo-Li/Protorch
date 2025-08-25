import sys
import time
import os
import json

# Add ROOT directory to sys.path
ROOT_DIR = str(__file__).rsplit("/", 3)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import base64
import streamlit as st
import streamlit_nested_layout


from streamlit_demo.modules.workflow_display import st_workflow_list, st_workflow_summary

def get_base64_of_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

st.set_page_config(
    page_title="ProtAgent - Workflow",
    page_icon="🔄",
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
        if st.button("Add New Workflow", icon=":material/add:"):
            st.success("New workflow creation is not implemented yet.")
        st_workflow_list()
    
    st.page_link("pages/chat.py", label="Back to chat", icon=":material/arrow_back:")  # Add a back button to the chat page

    st.title("Workflow Center")
    
    if st.session_state.get("workflow_selected"):
        # Check if workflow is from public or private source
        is_from_private = st.session_state.get("workflow_source", "private") == "private"
        
        st_workflow_summary(
            workflow=st.session_state.workflow_selected,
            show_save_module=False, open_expander=True)
        
        # Action buttons row
        if is_from_private:
            # Show both Start and Save to Public buttons for private workflows
            col1, col2, col3, col4 = st.columns([2, 3, 2, 3])
            
            with col1:
                if st.button("Start Workflow", icon=":material/play_circle:", use_container_width=True):
                    st.success("Workflow started successfully!")
            
            with col2:
                wf_name = st.text_input("Name for Public Save", key="workflow_public_name", label_visibility="collapsed", placeholder="Enter name for public save")
            
            with col3:
                save_public_clicked = st.button("Save to Public", icon=":material/save:", use_container_width=True)
            
            # Handle save to public logic
            if save_public_clicked:
                if not wf_name:
                    st.info("Please enter a name to save publicly")
                else:
                    workflow_item = {
                        "name": wf_name,
                        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                        "workflow": st.session_state.workflow_selected
                    }
                    public_dir = st.session_state.public_workflow_dir
                    os.makedirs(public_dir, exist_ok=True)
                    with open(os.path.join(public_dir, f"{wf_name}.json"), "w") as f:
                        json.dump(workflow_item, f, indent=4)
                    st.success(f"Saved to Public: {wf_name}")
                    st.rerun()  # Refresh to show the new workflow in the sidebar
        else:
            # Show only Start button for public workflows
            col1, col2 = st.columns([2, 8])
            
            with col1:
                if st.button("Start Workflow", icon=":material/play_circle:", use_container_width=True):
                    st.success("Workflow started successfully!")
    
    else:
        st.info("Start by selecting a workflow from the sidebar or creating a new one.")
