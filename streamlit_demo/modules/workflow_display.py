import json
import os
import time
from typing import Any, Dict, List
from collections.abc import Iterable as IterableType
import streamlit as st

from agent.workflow.workflow import Workflow
from streamlit_demo.components.file_msg import st_file_msg

def extract_path_results(data: Any) -> List[str]:
    """
    Recursively extracts all string values from a nested data structure.
    
    Args:
        data: The input data which can be a dict, list, tuple, set, or any nested combination
        
    Returns:
        List of all string values found in the nested structure
    """
    results = []
    
    # Base case: if it's a string, add it to results
    if isinstance(data, str):
        if os.path.exists(os.path.join(st.session_state.out_dir, data)):
            results.append(data)
    
    # Handle dictionaries: recursively process each value
    elif isinstance(data, Dict):
        for value in data.values():
            results.extend(extract_path_results(value))
    
    # Handle iterables (except strings): lists, tuples, sets, etc.
    elif isinstance(data, IterableType) and not isinstance(data, str):
        for item in data:
            results.extend(extract_path_results(item))
    
    return results


@st.fragment
def st_workflow_result_files(workflow:dict):
    with st.expander("Result files", expanded=False, icon=":material/file_download:"):
        
        workflow = {step_id: step for step_id, step in workflow.items() if step["tool"] != "chat"}
        
        results = [step_dict["results"] for step_dict in workflow.values() if "results" in step_dict]
        result_files = extract_path_results(results)
        
        if result_files:
            for file in result_files:
                
                for step_dict in workflow.values():
                    if "results" in step_dict and file in step_dict["results"]:
                        st.markdown(f"Result from **{step_dict['tool']}**")
                
                filepath = os.path.join(st.session_state.out_dir, file)
                st_file_msg(filepath, icon=":material/attachment:")

@st.fragment
def st_save_workflow(workflow_template: dict):
    with st.expander("Save this workflow", expanded=True, icon=":material/save:"):
        workflow_name = st.text_input(
            label="Workflow Name",
            key="workflow_id"
        )
        col1, col2, col3 = st.columns([1, 1, 8])
        with col1:
            workflow_name_submitted = st.button(
                icon=":material/save:",
                label="Save",
                key="workflow_name_submit",
                use_container_width=True
            )
        with col2:
            st.download_button(
                icon=":material/file_download:",
                label="Download",
                data=json.dumps(workflow_template, indent=4),
                file_name=f"{workflow_name}.json",
                disabled=not workflow_name_submitted or not workflow_name,
                mime="application/json",
                use_container_width=True
            )
        
        if workflow_name_submitted:
            if not workflow_name:
                st.info(f"Please enter a name for the workflow before saving.")
            else:
                workflow_item = {
                    "name": workflow_name,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "workflow": workflow_template
                }
                
                # Always save to private/my workflows directory
                workflow_dir = os.path.join(st.session_state.out_dir, "workflows")
                os.makedirs(workflow_dir, exist_ok=True)
                with open(os.path.join(workflow_dir, f"{workflow_name}.json"), "w") as f:
                    json.dump(workflow_item, f, indent=4)

                st.info(f"Workflow {workflow_name} saved successfully. Go to the Workflows page to view it.")
                st.page_link("pages/workflow.py", label="Workflow", icon="🔄")
        



@st.fragment
def st_workflow_summary(workflow:dict, show_save_module:bool=True, open_expander:bool=False):
    workflow_cls = Workflow.from_config(workflow, st.session_state.tool_manager)
    workflow_template = workflow_cls.to_template()
    
    with st.expander("Agent workflow", expanded=open_expander, icon=":material/workflow:"):
        graph = workflow_cls.visualize()
        st.write(graph)
        if show_save_module:
            st_save_workflow(workflow_template)


def _render_workflow_list_section(title: str, directory: str, key_prefix: str = "workflow"):
    st.markdown(f"### {title}")
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    display_dict = {}
    workflow_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    for i in range(len(workflow_files)):
        path = os.path.join(directory, workflow_files[i])
        try:
            with open(path, "r") as r:
                workflow_item = json.load(r)
            name = workflow_item.get("name", os.path.splitext(workflow_files[i])[0])
            ts = workflow_item.get("time", "1970-01-01 00:00:00")
            ymd = ts.split(" ")[0]
            key = f"{key_prefix}_{i}"
            display_dict[ymd] = [[path, name, key]] + display_dict.get(ymd, [])
        except Exception:
            continue
    display_dict = dict(sorted(display_dict.items(), key=lambda item: item[0], reverse=True))
    with st.container():
        for ymd, workflow_list in display_dict.items():
            st.markdown(f"#### {ymd}")
            for path, title, key in workflow_list:
                if st.button(title, use_container_width=True, key=key, disabled=st.session_state.get("is_chatting", False)):
                    with open(path, "r") as r:
                        workflow_item = json.load(r)
                        st.session_state.workflow_selected = workflow_item["workflow"]
                        # Track whether this is from public or private workflows
                        st.session_state.workflow_source = "public" if key_prefix == "public_workflow" else "private"
                        st.rerun()


def st_workflow_list():
    st.markdown("# Workflows")
    _render_workflow_list_section("My Workflows", st.session_state.workflow_dir, key_prefix="my_workflow")
    public_dir = st.session_state.public_workflow_dir
    _render_workflow_list_section("Public Workflows", public_dir, key_prefix="public_workflow")

