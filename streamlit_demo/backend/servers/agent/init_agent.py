import os
import yaml
import streamlit as st

# import sys
# ROOT_DIR = __file__.rsplit("/", 5)[0]
# if ROOT_DIR not in sys.path:
#     sys.path.append(ROOT_DIR)

from agent.agent.backbone import MultiAgentBackbone
from agent.tools.tool_manager import ToolManager


BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = __file__.rsplit("/", 5)[0]


def init_agent():
    config_path = f"{BASE_DIR}/../../../config.yaml"
    with open(config_path, 'r', encoding='utf-8') as r:
        config = yaml.safe_load(r)

    # Initialize the agent
    tool_manager = ToolManager(enable_quick_run=False)
    tool_manager.initialize_retriever()
    prot_agent = MultiAgentBackbone(**config["agent"], tool_manager=tool_manager)

    return prot_agent


prot_agent = init_agent()
