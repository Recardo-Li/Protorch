import os
import yaml
import streamlit as st

from agent.agent.sujin_protein_react_guidance import ProteinReActAgent
from agent.tools.tool_manager import ToolManager


@st.cache_resource()
def init_tool_manager():
    # Initialize the tool_manager
    tool_manager = ToolManager()
    return tool_manager


