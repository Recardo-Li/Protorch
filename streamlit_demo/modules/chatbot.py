import time
import re
import streamlit as st
import copy
import json
import os
from streamlit_extras.stylable_container import stylable_container
import json_repair
import streamingjson
import shortuuid

from contextlib import nullcontext
from typing import List, Dict
from streamlit_demo.components.error_display import display_timer, reset_error_display
from streamlit_demo.components.plan_detail import st_plan_detail
from streamlit_demo.modules.workflow_display import st_workflow_result_files, st_workflow_summary
from streamlit_demo.modules.chat_history import get_chat_id, save_chat
from agent.utils.constants import AGENT_STATUS, AgentResponse
from streamlit_demo.components.file_msg import st_file_msg
from streamlit_demo.components.tool_form import st_tool_form
from streamlit_demo.backend.frontend_api import get_agent_response, terminate, change_tool_call
from streamlit_demo.modules.file_browser import st_file_uploader
from streamlit_demo.modules.chat_history import st_new_chat

from agent.workflow.workflow import Workflow


def display_chat_messages(messages: List[Dict]) -> List[Dict]:
    """
    Display chat messages in the Streamlit app.
    Args:
        messages: Each message is a dictionary with the following keys:
            - role: The role of the speaker. Should be one of ["user", "assistant"].
            - content: The content of the message.
            - file: List of file paths uploaded by the speaker.
            - error: Error message.
    
    Returns:
        Processed messages that can be used to generate agent responses.
    """

    messages = copy.deepcopy(messages)
    for message in messages:
        with st.chat_message(message["role"]):
            # IMPORTANT: The container is used to overwrite previous messages when app reruns
            context = nullcontext if st.session_state.get("is_chatting", False) else st.container
            with context():
                if message["role"] == "user":
                    # If the user uploaded files, display them
                    for file in message["file"]:
                        filepath = os.path.join(st.session_state.out_dir, file)
                        st_file_msg(filepath, icon=":material/attachment:")
                    st.markdown(message["content"])
                
                elif message["role"] == "assistant":
                    # st.write(message)
                    
                    label = "Thoughts"
                    state = "complete"
                    if (e := message.get("error", None)) is not None:
                        label = "Error"
                        state = "error"
                    
                    # First display the thinking status
                    with st.status(label=label, state=state, expanded=False) as status:
                        with st.container():
                            css = '''
                            <style>
                                [data-testid="stExpander"] div:has(>.stCode) {
                                    overflow: auto;
                                    overflow-x: hidden;
                                    max-height: 300px;
                                }
                            </style>
                            '''
                            st.markdown(css, unsafe_allow_html=True)
                            display_agent_thoughts(message["content"])
                    
                    # Display error message
                    if (e := message.get("error", None)) is not None:
                        st.error(e)
                        # st.error("The system is busy. Please try again later.")
                    
                    # Then display the final response
                    try:
                        # st.write(json_repair.loads(message["content"]))
                        answer = json_repair.loads(message["content"])[-2]

                        if answer["sender"] == "responder":
                            if isinstance(answer, str):
                                answer = json_repair.loads(answer)
                            st.write(answer["content"])
                        
                        
                        workflow = message.get("workflow", st.session_state.get("workflow", ""))
                        if isinstance(workflow, str):
                            workflow = json_repair.loads(workflow)
                        
                        # st.write(workflow)
                        
                        valid_workflow = workflow.get("valid_workflow", True)
                        # st.write(valid_workflow)
                        
                        workflow = {step_id: step for step_id, step in workflow.items() if isinstance(step, dict) and step.get("tool") != "chat"}
                        
                        # st.write(workflow)
                        
                        st_workflow_result_files(workflow)
                        
                        
                        if valid_workflow and len(workflow):
                            st_workflow_summary(workflow)
                        
                    except:
                        pass
                    
            # Add file names to the prompt
            if message["file"] and message["role"] == "user":
                file_prompt = "I have uploaded the following files:\n" + "\n".join(['"'+message+'"' for message in message["file"]])
                message["content"] = f"{file_prompt}\n{message['content']}"


    return messages


def display_agent_thoughts(content: str):
    """
    Display the agent's thoughts
    Args:
        content: The content of the agent's response
    """
    plan_set = []
    current_plan_dict = {}
    active_subagent = None
    last_msg = None
    for msg in json_repair.loads(content):
        if isinstance(msg, str):
            msg = json_repair.loads(msg)
        
        if isinstance(msg, dict):
            try:
                sender = msg.get("sender", None)
                content = msg.get("content", None)
                
                active_subagent = sender
                last_msg = msg
                
                if sender is None or content is None:
                    continue
                
                if isinstance(content, str):
                    content = json_repair.loads(content)
                
                
                if sender == "planner":
                    if len(current_plan_dict):
                        plan_set.append(current_plan_dict)
                        current_plan_dict = {}
                    current_plan_dict = content
                    
                elif sender == "tool_executor":
                    current_step = content.get("current_step", None)
                    if not current_step:
                        continue
                    if current_step not in current_plan_dict:
                        continue
                    if current_plan_dict[current_step].get("tool") != content.get("tool_name"):
                        continue
                    current_plan_dict[current_step].update(content)
                else:
                    other_agent = sender
            except Exception as e:
                # raise
                pass
    
    plan_set.append(current_plan_dict)
    
    content_uid = shortuuid.uuid()
    
    st_plan_detail(plan_set, content_uid)

    if st.session_state.get("is_chatting") and active_subagent:
        st.info(f"**{' '.join(active_subagent.split('_'))}** is thinking...", icon=":material/mindfulness:")
        if last_msg is not None and active_subagent not in ["planner", "tool_executor"]:
            with st.expander("Connection Thoughts", expanded=True, icon=":material/automation:"):
                # st.write(last_msg)
                if isinstance(last_msg, str):
                    last_msg = json_repair.loads(last_msg)
                if isinstance(last_msg, dict):
                    last_analysis = last_msg.get("analysis")
                    if last_analysis:
                        st.write(last_analysis)
                    
                    else:
                        last_content = last_msg.get("content", {})
                        if isinstance(last_content, str):
                            last_content = json_repair.loads(last_content)
                        if isinstance(last_content, dict):
                            last_thoughts = last_content.get("analysis")
                            if last_thoughts:
                                st.write(last_thoughts)

@st.fragment()
# Streamed response emulator
def response_generator(messages: List[Dict]):
    """
    Args:
        messages: Each message is a dictionary with the following keys:
            - role: The role of the speaker. Should be one of ["user", "assistant"].
            - content: The content of the message.
    """
    try:
        # Continually generate a response or generate from scratch
        stream_output = st.session_state.get("stream_output", None)
        if stream_output is None:
            stream_output = get_agent_response(st.session_state.out_dir, messages)
            # Record the ip address of the agent node
            st.session_state.ip_port = next(stream_output)
            st.session_state.stream_output = stream_output
            
        # Display the thinking status
        with st.status("Thinking...", expanded=False) as status:
            with st.empty():
                for agent_response in stream_output:
                    # Trace the running status
                    if "ip_port" not in agent_response:
                        raise Exception(agent_response)
                    
                    # The agent is generating the final response
                    if agent_response.status == AGENT_STATUS.FINAL_RESPONSE:
                        break
        
                    elif agent_response.status == AGENT_STATUS.GENERATING or agent_response.status == AGENT_STATUS.TOOL_RUNNING:
                        with st.container():
                            display_agent_thoughts(agent_response.content)
                        # Save the intermediate response
                        st.session_state.content = agent_response.content
                        st.session_state.workflow = agent_response.workflow
        
                    # If the agent is calling a tool, create a tool call form for the user to check and submit
                    elif agent_response.status == AGENT_STATUS.TOOL_CALLING:
                        # Only when the user turns on the confirmation mode
                        if st.session_state.tool_call_confirmation:
                            tool_name = agent_response.tool_arg["name"]
                            tool_args = agent_response.tool_arg["args"]
            
                            if tool_name != "chat":
                                with st.container():
                                    display_agent_thoughts(agent_response.content)
                                    st_tool_form(tool_name, tool_args)
                                
                                # Expand the status to show the tool call form
                                status.update(expanded=True, label="Calling a tool", state="error")
                                break
                        
                        else:
                            tool_dict = agent_response.tool_arg
                            change_tool_call(st.session_state.ip_port, tool_dict["name"], tool_dict["args"])
                        
        
        # Display the final response
        if agent_response.status == AGENT_STATUS.FINAL_RESPONSE:
            # Record the start position of the final response
            with st.empty():
                for agent_response in stream_output:
                    if agent_response.status == AGENT_STATUS.FINAL_RESPONSE:
                        content = json_repair.loads(agent_response.content)[-1]
                        try:
                            if isinstance(content, str):
                                content = json_repair.loads(content)
                            if content["sender"] == "responder" and content["content"] is not None:
                                st.write(content["content"])
                        except:
                            pass
                        
                        # Save the intermediate response
                        st.session_state.content = agent_response.content
                    
                    elif agent_response.status == AGENT_STATUS.WORKFLOW:
                        st.info("Summarizing the workflow...", icon=":material/workflow:")
                    
                    elif agent_response.status == AGENT_STATUS.TITLE:
                        final_response = json_repair.loads(agent_response.content)[-2]
                        st.write(final_response)

                        st.info("Summarizing the title...", icon=":material/workflow:")
                        st.session_state.workflow = agent_response.workflow
                        # st.write(agent_response.workflow)
                    
                    elif agent_response.status == AGENT_STATUS.IDLE:
                        st.session_state.is_chatting = False
                        if agent_response.get("error", None) is not None:
                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "content": st.session_state.content,
                                    "file": [],
                                    "workflow": st.session_state.workflow,
                                    "error": agent_response["error"]
                                }
                            )
                        else:
                            files = []
                            tool_args = agent_response.get("tool_arg", None)
                            if tool_args:
                                files = tool_args.get("file", [])
                            st.session_state.messages.append(
                                {
                                    "role": "assistant", 
                                    "content": agent_response.content, 
                                    "file": files, 
                                    "workflow": agent_response.workflow})

                        # Response finished. Save this chat
                        save_chat()
                        st.rerun()

        
        if agent_response.status == AGENT_STATUS.ERROR:
            st.session_state.is_chatting = False
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": st.session_state.content,
                    "workflow": st.session_state.workflow,
                    "file": [],
                    "error": agent_response["error"]
                }
            )
            save_chat()
            st.rerun()
                        
    except Exception as e:
        st.write(st.session_state.messages)
        
        # Record error message
        st.session_state.is_chatting = False
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": st.session_state.content,
                "workflow": st.session_state.workflow,
                "file": [],
                "error": str(e)
            }
        )
        try:
            terminate(st.session_state.ip_port)
        except:
            pass
        save_chat()
        raise
        st.rerun()
        


def st_chatbot():
    """
    Display a chatbot in the Streamlit app.
    """
    # Accept user input
    # if prompt := st.chat_input("What is up?"):

    # If no user input, give a greeting message
    messages = st.session_state.get("messages", [])
    
    with st.container(height=1000):
        if not messages:
            st.markdown("# Welcome to ProtAgent!")

        # Otherwise display chat history
        else:
            # Display user message
            processed_messages = display_chat_messages(messages)

            # Generate assistant response
            if st.session_state.get("is_chatting", False):
                # If user stops generation, get the intermediate response
                if st.button("Stop generation", disabled=st.session_state.is_stopping):
                    st.session_state.messages.append(
                        {"role": "assistant", 
                         "content": st.session_state.content, 
                         "file": [],
                         "workflow": st.session_state.workflow,}
                    )

                    st.session_state.is_chatting = False
                    st.session_state.is_stopping = True
                    save_chat()
                    st.rerun()

                # Otherwise, generate the full response
                else:
                    with st.chat_message("assistant"):
                        response_generator(processed_messages)

            # Terminate the running agent
            elif st.session_state.get("is_stopping", False):
                st.markdown("*Stopping the generation...* \n\n This might take about **1 min**, please wait...")

                # Terminate the running tool
                terminate(st.session_state.ip_port)

                st.session_state.is_stopping = False
                st.rerun()
    
    if st.session_state.get("messages", []) == []:
        for file in st.session_state.get("sent_files", []):
            filepath = os.path.join(st.session_state.out_dir, file)
            st_file_msg(filepath, icon=":material/attachment:")
    
    col1, col2 = st.columns([8, 1])
    if not messages or st.session_state.get("is_chatting", False):
        with col1:
            if prompt := st.chat_input("What's up?", disabled=(st.session_state.get("messages", []) != [])):
                # Add user message to chat history
                sent_files = st.session_state.get("sent_files", [])
                st.session_state.messages = [{"role": "user", "content": prompt, "file": sent_files}]
                
                # Set chat flags
                st.session_state.is_chatting = True     # Whether the agent is generating response
                st.session_state.is_stopping = False    # Whether the user has stopped generation
                st.session_state.stream_output = None   # The response stream
                st.session_state.content = ""   # Store the response
                st.session_state.workflow = ""  # Store the workflow
                st.session_state.ip_port = None     # Connect to the agent
                st.session_state.chat_id = get_chat_id()
                
                st.session_state.sent_files = []
                st.rerun()
    
        with col2:
            add_col, clear_col = st.columns(2)
            with add_col:
                with stylable_container(
                    key="chat_input",
                    css_styles=["""
                    div{
                    }""",
                    """
                    div{
                        float: right;
                    }
                    """]
                ):
                    with st.popover("Add files", disabled=st.session_state.get("is_chatting", False)) as popover:
                        st_file_uploader(st.session_state.out_dir)
            
            with clear_col:
                with stylable_container(
                    key="clear_files",
                    css_styles=["""
                    div{
                    }""",
                    """
                    div{
                        float: right;
                    }
                    """]
                ):
                    if st.button("Clear files", disabled=st.session_state.get("is_chatting", False)):
                        st.session_state.sent_files = []
                        st.rerun()
    
    else:
        st.info("Currently we only support single-turn conversation. Please create a new conversation to chat with our agent.")
        if st.button(label="New conversation",key="new_conversation_btn",icon=":material/add:", disabled=(st.session_state.get("is_chatting", False) or st.session_state.get("messages", []) == [])):
            st_new_chat()
