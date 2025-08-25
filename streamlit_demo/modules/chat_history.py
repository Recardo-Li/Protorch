import streamlit as st
import os
import json
import json_repair
import time

from easydict import EasyDict


def get_chat_id() -> int:
    """
    Return current chat id
    """
    return len(os.listdir(st.session_state.chat_history_dir))


def save_chat():
    """
    Save current chat
    """
    chat_history = {
        "messages": st.session_state.messages,
        "workflow": st.session_state.workflow,
        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
    }
    
    save_path = f"{st.session_state.chat_history_dir}/{st.session_state.chat_id}.json"
    try:
        with open(save_path, "w") as w:
            json.dump(chat_history, w, indent=4)
    except Exception as e:
        os.remove(save_path)
        st.error(f"Error saving chat history: {e}")
        

def st_chat_history():
    """
    Display the chat history
    """

    st.markdown("# Chat history")
    
    # Get basic information of each chat
    display_dict = {}
    chat_files = os.listdir(st.session_state.chat_history_dir)
    for i in range(len(chat_files)):
        path = os.path.join(st.session_state.chat_history_dir, f"{i}.json")
        with open(path, "r") as r:
            # Get the chat title and chat time
            chat_dict = EasyDict(json.load(r))
            
            # Skip empty chat history
            try:
                last_msg = json_repair.loads(chat_dict.messages[-1].content)[-1]
                if isinstance(last_msg, dict) and last_msg["sender"] == "namer":
                    title = last_msg["content"]
                else:
                    title = f"Incomplete chat"
                time = chat_dict["time"]
                
                # Group chats by time
                ymd = time.split(" ")[0]
                key = f"chat_history_{i}"
                display_dict[ymd] = [[path, title, key]] + display_dict.get(ymd, [])
            
            except Exception as e:
                pass
    
    # Sort the chat history by ymd
    display_dict = dict(sorted(display_dict.items(), key=lambda item: item[0], reverse=True))
    
    # Display chat history
    with st.container():
        for ymd, chat_list in display_dict.items():
            st.markdown(f"## {ymd}")
            
            for path, title, key in chat_list:
                icon = None
                if title == "Incomplete chat":
                    icon = ":material/running_with_errors:"
                if st.button(title, use_container_width=True, key=key, disabled=st.session_state.get("is_chatting", False), icon=icon):
                    # Load chat history:
                    with open(path, "r") as r:
                        chat_dict = EasyDict(json.load(r))
                        st.session_state.messages = chat_dict.messages
                        st.session_state.workflow = chat_dict.get("workflow", "")
                        
                        st.rerun()

def st_new_chat():
    """
    Create a new chat
    """
    st.session_state.messages = []
    st.session_state.workflow = ""
    st.session_state.selected_files = []
    st.session_state.sent_files = []

    st.rerun()