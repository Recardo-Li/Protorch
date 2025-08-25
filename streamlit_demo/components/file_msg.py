import streamlit as st
import os

from streamlit_demo.components.file_preview import file_preview
from streamlit_demo.modules.file_browser import show_all_files

BASE_DIR = os.path.dirname(__file__)

def st_file_msg(file_path: str, icon=None, enable_download: bool = False):
    """
    This function is used to display a file in a chatbot
    Args:
        file_path: Path to the file.
    """
    file_name = os.path.basename(file_path)
    
    with st.expander(file_name, icon=icon):
        # If this path is a directory
        if os.path.isdir(file_path):
            st.write(f"This is a directory. Go to the Files page to view it.")
            st.page_link("pages/files.py", label="Files", icon="📁")
        else:
            file_preview(file_path)
            st.markdown("**Note**: *Copy this file path to reference in future conversations for further analysis.*")
            st.code(file_path[st.session_state.out_dir.__len__()+1:], language="plaintext")
            if enable_download:
                with open(file_path, "rb") as fp:
                    data = fp.read()
                    st.download_button("Download", data=data, file_name=file_name)
