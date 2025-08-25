import json
from graphviz import Digraph
from typing import Dict, Any, List, Optional

from agent.tools.base_tool import BaseTool
from agent.utils.constants import TOOLNODE_STATUS


class ToolNode:
    """
    Represents a single step in the workflow, wrapping a BaseTool instance.
    
    This class tracks the origin of each of the tool's parameters.
    """
    def __init__(self, node_id: str, tool: BaseTool):
        """
        Initializes a ToolNode.
        
        Args:
            node_id (str): A unique identifier for this node in the workflow (e.g., 'step_1').
            tool (BaseTool): An instance of a tool.
        """
        self.node_id = node_id
        self.tool = tool
        self.status = TOOLNODE_STATUS.INIT
        self.parameter_origins: Dict[str, Dict[str, Any]] = {}
        self.tool_args: Dict[str, Any] = {}
        self.results = {}
        
        self._initialize_parameter_origins()

    def _initialize_parameter_origins(self):
        """
        Sets the initial origin for all parameters.
        Required parameters come from 'user_input'.
        Optional parameters come from 'default'.
        """
        print(f"Initializing node '{self.node_id}' with tool '{self.tool.tool_name}':")
        
        # Handle required parameters
        for param in self.tool.config.document.get("required_parameters", []):
            param_name = param['name']
            self.parameter_origins[param_name] = {'source': 'user_input'}

        # Handle optional parameters
        for param in self.tool.config.document.get("optional_parameters", []):
            param_name = param['name']
            self.parameter_origins[param_name] = {'source': 'default'}

    def __repr__(self) -> str:
        return f"ToolNode(id='{self.node_id}', tool='{self.tool.name}')"
