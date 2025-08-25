import streamlit as st
import os

from streamlit_demo.components.file_preview import dialog_file_preview


def get_num_files(file_dir: str) -> int:
    """
    Get the number of all files in a directory, including subdirectories.
    Args:
        file_dir: Directory path

    Returns:
        num_files: Number of files
    """
    num_files = 0
    for root, dirs, files in os.walk(file_dir):
        num_files += len(files)
    return num_files
   

def show_all_files(root_dir: str, now_dir: str, selected: bool = False):
    """
    Show all files in the current directory.
    Args:
        root_dir: Root directory
        now_dir: Current directory
        selected: Default selected status
    """
    browser_disabled = st.session_state.get("is_chatting", False)
    
    # Distinguish between files and directories
    file_list = []
    dir_list = []
    for file in os.listdir(now_dir):
        if os.path.isfile(os.path.join(now_dir, file)):
            file_list.append(file)
        else:
            dir_list.append(file)

    # Display all directories
    for dir_name in dir_list:
        sub_dir_path = os.path.join(now_dir, dir_name)
        if get_num_files(sub_dir_path) == 0:
            continue
        
        col_1, col_2 = st.columns([1, 50])
        with col_1:
            dir_check = st.checkbox("s", key=sub_dir_path, value=selected, disabled=browser_disabled,
                                    label_visibility="hidden")
            
        with col_2:
            with st.expander(f"**{dir_name}**/"):
                show_all_files(root_dir, sub_dir_path, selected=dir_check)
    
    # Display all files
    for file_name in file_list:
        # Only display the relative path
        path = os.path.join(now_dir, file_name).replace(root_dir, "")
        if path.startswith("/"):
            path = path[1:]

        if st.session_state.get("send_btn") is True and path in st.session_state:
            st.session_state[path] = False
        
        file_check = st.checkbox(file_name, key=path, value=selected, disabled=browser_disabled)
        
        
        if file_check:
            if path not in st.session_state.selected_files:
                st.session_state.selected_files.append(path)
                
        else:
            if path in st.session_state.selected_files and st.session_state.get("send_btn") is not True:
                st.session_state.selected_files.remove(path)
        
        


def st_file_manager(file_dir: str):
    """
    Custom implementation of a file manager.
    Args:
        file_dir: Directory path
    """

    # Store selected files and can be accessed from other components
    st.session_state.selected_files = []
    browser_disabled = st.session_state.get("is_chatting", False)

    # Title

    # File uploader
    # Change the key to initialize a new file uploader
    upload_cnt = st.session_state.get("upload_cnt", 0) + 1
    uploaded_file = st.file_uploader("Upload a file", key=f"upload_{upload_cnt}",
                                     disabled=browser_disabled)

    if uploaded_file is not None:
        # Upload the file
        bytes_data = uploaded_file.getvalue()
        save_path = os.path.join(file_dir, uploaded_file.name)
        with open(save_path, "wb") as wb:
            wb.write(bytes_data)

        # Refresh the file uploader
        st.session_state.upload_cnt = upload_cnt
        st.rerun(scope="fragment")

    # List all files
    select_all = st.checkbox("**Select all**", key="select_all", disabled=browser_disabled)
    with st.container(border=True, height=500):
        show_all_files(file_dir, file_dir, selected=select_all)

    # Display buttons
    preview_col, delete_col = st.columns(2)

    # This button is to preview a selected file
    with preview_col:
        preview_disabled = len(st.session_state.selected_files) != 1 or browser_disabled
        if st.button("Preview", use_container_width=True, disabled=preview_disabled) and len(st.session_state.selected_files) == 1:
            path = os.path.join(file_dir, st.session_state.selected_files[0])
            dialog_file_preview(path)

    # This button is to delete selected files
    with delete_col:
        if len(st.session_state.selected_files) == 0:
            del_text = "Delete"
            del_disabled = True
        else:
            del_text = f"Delete ({len(st.session_state.selected_files)})"
            del_disabled = False

        del_disabled = del_disabled or browser_disabled
        if st.button(del_text, use_container_width=True, disabled=del_disabled):
            for file in st.session_state.selected_files:
                path = os.path.join(file_dir, file)
                os.remove(path)
            st.rerun(scope="fragment")
    
    # This button is to download a selected file

    if len(st.session_state.selected_files) == 1:
        path = os.path.join(file_dir, st.session_state.selected_files[0])
        with open(path, "rb") as fp:
            data = fp.read()
            file_name = os.path.basename(st.session_state.selected_files[0])
            st.download_button("Download", data=data, file_name=file_name, use_container_width=True,
                                disabled=browser_disabled)
    else:
        st.button("Download", use_container_width=True, disabled=True)


@st.fragment
def st_file_uploader(file_dir: str):
    """
    Upload files to conversation.
    Args:
        file_dir: Directory path
    """
    
    # Store selected files and can be accessed from other components
    if st.session_state.get("selected_files") is None:
        st.session_state.selected_files = []
    browser_disabled = st.session_state.get("is_chatting", False)

    # Title

    # File uploader
    # Change the key to initialize a new file uploader
    upload_cnt = st.session_state.get("upload_cnt", 0) + 1
    uploaded_file = st.file_uploader("Upload a file", key=f"upload_{upload_cnt}",
                                     disabled=browser_disabled)

    if uploaded_file is not None:
        # Upload the file
        bytes_data = uploaded_file.getvalue()
        save_path = os.path.join(file_dir, uploaded_file.name)
        with open(save_path, "wb") as wb:
            wb.write(bytes_data)

        # Refresh the file uploader
        st.session_state.upload_cnt = upload_cnt
        st.rerun(scope="fragment")

    # List all files
    select_all = st.checkbox("**Select all**", key="select_all", disabled=browser_disabled)
    with st.container(border=True, height=300):
        show_all_files(file_dir, file_dir, selected=select_all)

    if st.button("Send to conversation", key="send_btn",disabled=len(st.session_state.selected_files) == 0):
        st.session_state.sent_files = st.session_state.selected_files
        st.session_state.selected_files = []
        st.rerun()