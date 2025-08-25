import streamlit as st
import time
import os

from streamlit_demo.backend.frontend_api import change_tool_call


# Mapping the argument type to the corresponding widget
TYPE_TO_WIDGET = {
    "SEQUENCE": st.text_input,
    "PATH": st.text_input,
    "TABLE": st.text_input,
    "TEXT": st.text_input,
    "SELECTION": st.selectbox,
    "MOLECULE": st.text_input,
    "DATE": st.text_input,
    "INTEGER": st.text_input,
    "FLOAT": st.text_input,
    "UNIPROT_ID": st.text_input,
    "PFAM_ID": st.text_input,
    "PDB_ID": st.text_input,
    "DICT": st.text_input,
    "LIST": st.text_input,
}


def modify_tool_call():
    """
    Modify the tool call based on the user input
    """
    
    tool_call = st.session_state.tool_call
    change_tool_call(st.session_state.ip_port, tool_call["name"], tool_call["args"])
    st.write(tool_call)
    # raise


@st.fragment
def create_input_arg(arg_dict: dict, t, value=None):
    """
    Create an input argument based on the argument dictionary and value
    Args:
        arg_dict: Argument dictionary
        t: Time when the argument is created. Used to create a new key for the argument
        value: Value of the argument
    """
    key = f"{arg_dict.name}_{t}"
    
    arg_type = arg_dict.type
    if arg_type in TYPE_TO_WIDGET:
        st.markdown(f"- {arg_dict.name.strip()}")
        st.markdown(f"*{arg_dict.description.strip()}*")
        
        with st.container(border=True):
            # For some argument types, we enable the user to upload a file
            if arg_type in ["PATH", "FASTA", "TABLE"]:
                # Change the key to initialize a new file uploader
                upload_cnt = st.session_state.get(f"upload_{arg_dict.name}_cnt", 0) + 1
                uploaded_file = st.file_uploader("Upload a file", key=f"upload_{arg_dict.name}_{upload_cnt}")
                if uploaded_file is not None:
                    # Upload the file
                    bytes_data = uploaded_file.getvalue()
                    save_path = os.path.join(st.session_state.out_dir, uploaded_file.name)
                    with open(save_path, "wb") as wb:
                        wb.write(bytes_data)
                    
                    st.session_state[f"upload_{arg_dict.name}_cnt"] = upload_cnt
                    st.session_state[f"upload_{arg_dict.name}_value"] = save_path
                    st.rerun(scope="fragment")
            
            if st.session_state.get(f"upload_{arg_dict.name}_value", None) is not None:
                value = st.session_state[f"upload_{arg_dict.name}_value"].replace(st.session_state.out_dir, "")
                if value.startswith("/"):
                    value = value[1:]
                st.session_state[f"upload_{arg_dict.name}_value"] = None
                
            if arg_type == "SELECTION":
                arg = TYPE_TO_WIDGET[arg_type](arg_dict.name, arg_dict.choices, index=arg_dict.choices.index(value),
                                               key=key)
            else:
                arg = TYPE_TO_WIDGET[arg_type](arg_dict.name, value=value, label_visibility="collapsed", key=key)
                
        # Save the argument
        st.session_state.tool_call["args"][arg_dict.name] = arg
        

def reset_tool_form_state():
    """
    Reset the tool form state
    """
    
    # # Indicate whether the tool form is completed
    # st.session_state.tool_form_completed = False
    
    # Countdown timer
    st.session_state.time_limit = 60
    st.session_state.now_time = st.session_state.time_limit

    # Key of the tool selectbox
    st.session_state.tool_selectbox_key = time.time()


@st.fragment(run_every=1)
def countdown_timer():
    """
    Set a countdown timer
    """
    if st.session_state.now_time == 0:
        modify_tool_call()
        st.rerun()
    else:
        st.session_state.now_time -= 1
        percentage = int(st.session_state.now_time / st.session_state.time_limit * 100)

        st.markdown(f"Please complete within <font color='red'>{st.session_state.now_time}</font> seconds",
                    unsafe_allow_html=True)
        st.progress(percentage)


@st.fragment
def create_tool_call(tool_name: str, agent_kwargs: dict):
    """
    Create a tool call
    Args:
        tool_name: Name of the tool
        agent_kwargs: Tool arguments given by the agent
    """
    tool_manager = st.session_state.tool_manager

    st.markdown("#### The agent attempts to call a tool")
    st.markdown("You can **modify** the arguments below and **submit** this form to run the tool.")

    all_tools = list(tool_manager.tools.keys())
    selected_tool = st.selectbox("Tool", all_tools, index=all_tools.index(tool_name),
                                 key=st.session_state.tool_selectbox_key)

    # Tool description
    doc_dict = tool_manager.get_tool(selected_tool).config.document
    st.markdown(f"*{doc_dict.tool_description}*")

    # Input arguments
    st.session_state.tool_call = {"name": selected_tool, "args": {}}
    if len(doc_dict.required_parameters) > 0:
        st.markdown("**Required arguments**")
    for arg_dict in doc_dict.required_parameters:
        value = agent_kwargs[arg_dict.name] if arg_dict.name in agent_kwargs else None
        create_input_arg(arg_dict, time.time(), value)
    
    # Show optional arguments
    with st.expander("**Optional arguments**"):
        for arg_dict in doc_dict.optional_parameters:
            # Set default value
            value = arg_dict.default
            create_input_arg(arg_dict, time.time(), value)
    
    # Wrap the submit button in a fragment to avoid rerunning the entire form
    @st.fragment
    def submit():
        # If the user submits the form
        if st.button("Submit"):
            modify_tool_call()
            st.rerun()
    
    submit()


def st_tool_form(tool_name: str, agent_kwargs: dict):
    """
    Display a form to input the arguments of a tool
    Args:
        tool_name: Name of the tool
        
        agent_kwargs: Tool arguments given by the agent. Note the arguments may not match the tool's requirements,
            so they need to be processed before being passed to the tool.
    """
    reset_tool_form_state()
    
    try:
        with st.container(border=True):
            # Set a countdown timer
            countdown_timer()
     
            # Create a tool call
            create_tool_call(tool_name, agent_kwargs)
    
    except Exception as e:
        st.error(e)
        # raise e
    