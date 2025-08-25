import itertools
import random
import sys
import json_repair

from easydict import EasyDict


ROOT_DIR = __file__.rsplit("/", 3)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
from agent.tools.tool_manager import ToolManager
from agent.workflow.workflow import Workflow
from agent.utils.constants import TOOLNODE_STATUS



class WorkflowManager:
    def __init__(self, tool_manager: ToolManager):
        """
        Initialize the WorkflowManager with a ToolManager.
        Args:
            tool_manager: An instance of ToolManager that manages the tools.
        """
        self.tool_manager = tool_manager
        self.transfer_matrix = self.build_transfer_matrix()
        
        self.query_io = None
        self.workflow = None
        self.current_args = {}
        self.current_step = "input"
        self.valid_workflow = True
    
    def workflow2json(self):
        if self.workflow is None:
            return {}
        else:
            return self.workflow.to_json()
    
    def workflow_length(self):
        if self.workflow is None:
            return 0
        else:
            return len(self.workflow.nodes)
    
    def set_query_io(self, query_parser_output):
        if not isinstance(query_parser_output, dict):
            query_parser_output = json_repair.repair_json(query_parser_output)
        io_types = {k: v for k, v in query_parser_output.items() if k=="input" or k=="output"}
        
        # Update arg pool. This retrial is launched from tool monitor
        if self.query_io is not None:
            # TODO
            previous_input_tools = self.query_io.get("input", {}).keys()
            self.current_args = {k: v for k, v in self.current_args.items() if k not in previous_input_tools}
            self.current_args.update(io_types.get("input", {}))
        
        self.query_io = io_types

    def set_workflow(self, planner_output):
        if not isinstance(planner_output, dict):
            planner_output = json_repair.repair_json(planner_output)
        plan = {k: v for k, v in planner_output.items() if k.startswith("step_")}
        self.workflow = Workflow.from_config(plan, self.tool_manager)

    def connect_tool_node(self, connector_output):
        if not isinstance(connector_output, dict):
            connector_output = json_repair.repair_json(connector_output)
        
        if "error" in connector_output:
            raise ValueError(f"Connector output contains error: {connector_output['error']}")
        
        connection_plan = connector_output["connection"]
        current_step = connector_output["current_step"]
        
        for target_para, connection in connection_plan.items():
            if connection["source"] != "user_input":
                self.workflow.connect(
                    upstream_node_id = connection["source_id"],
                    upstream_output_name = connection["source_parameter"],
                    downstream_node_id = current_step,
                    downstream_input_name = target_para
                )
            
        self.workflow.nodes[current_step].status = TOOLNODE_STATUS.CONNECTED
        
    def execute_toolnode(self, executor_output):
        if not isinstance(executor_output, dict):
            executor_output = json_repair.repair_json(executor_output)
        
        executor_keys = ["current_step", "tool_name", "tool_arg", "status", "results"]
        executor_output = {k: v for k, v in executor_output.items() if k in executor_keys}
        
        current_step = executor_output["current_step"]
        self.current_step = current_step
        
        status = executor_output["status"]
        
        if status == "success":
            self.workflow.nodes[current_step].results = executor_output.get("results")
            self.workflow.nodes[current_step].tool_args = executor_output.get("tool_arg")
            self.workflow.nodes[current_step].status = TOOLNODE_STATUS.EXECUTED
        else:
            raise ValueError(f"Tool execution failed.")
    
    def insert_tool_chain(self, connector_output):
        if not isinstance(connector_output, dict):
            connector_output = json_repair.repair_json(connector_output)
        if "error" not in connector_output:
            raise ValueError("Only insert tool chain when conncetor failed")
        
        connector_keys = ["current_step", "arguments_pool", "missing_types"]
        
        current_node_id = connector_output["current_step"]
        if current_node_id not in self.workflow.nodes:
            raise ValueError(f"Current step {current_node_id} not found in the workflow.")
        
        arguments_pool = connector_output["arguments_pool"]
        available_types = [para["detailed_type"] for para in arguments_pool]
        
        added_tools = {}
        for target_type in connector_output["missing_types"]:
            possible_paths = []
            for source_type in available_types:
                # Find all paths from source_type to target_type
                paths = self.find_path(source_type, target_type)
                if paths:
                    possible_paths.extend(paths)
            
            if possible_paths:
                min_length = min(len(path) for path in possible_paths)
                shortest_paths = [path for path in possible_paths if len(path) == min_length]
                
            else:
                raise ValueError(f"No available tool chain to convert {source_type} to {target_type}.")
            
            added_tools[target_type] = shortest_paths
        
        # Decide the shortest paths when considering obtaining all missing types
        overall_shortest_paths = []
        for item in itertools.product(*added_tools.values()):
            path = []
            for p in item:
                path.extend(p)
            overall_shortest_paths.append(path)
        
        # Use set to remove duplicates because the same tool can be used to obtain different missing types
        min_length = min([len(set(path)) for path in overall_shortest_paths])
        overall_shortest_paths = [path for path in overall_shortest_paths if len(set(path)) == min_length]
        
        # Remove duplicates while keeping the order
        final_paths = []
        for path in overall_shortest_paths:
            seen = set()
            filtered_path = []
            for tool in path:
                if tool not in seen:
                    seen.add(tool)
                    filtered_path.append(tool)
            
            final_paths.append(filtered_path)
        
        # Randomly select one path and add it to the plan
        added_tools = random.choice(final_paths)
        
        added_tool_instances = [self.tool_manager.tools[tool_name] for tool_name in added_tools]
        
        self.workflow.insert_nodes_before(
            tool_chain = added_tool_instances,
            current_node_id= current_node_id
        )
    
    def build_transfer_matrix(self) -> dict:
        """
        Build the transfer matrix for the tools.
        """
        # Record how can a input type be converted to another type by a tool
        transfer_matrix = {}
        for tool_name, obj in self.tool_manager.tools.items():
            doc = obj.config.document
            input_types = set([param["detailed_type"] for param in doc.required_parameters])
            output_types = set([param["detailed_type"] for param in doc.return_values])
            
            if len(input_types) == 1:
                input_type = input_types.pop()
                # Each output type can be generated given the input type and the tool
                if input_type not in transfer_matrix:
                    transfer_matrix[input_type] = {output_type: [tool_name] for output_type in output_types}
                
                else:
                    for output_type in output_types:
                        transfer_matrix[input_type][output_type] = transfer_matrix[input_type].get(output_type, []) + [
                            tool_name]
        
        return transfer_matrix
    
    def find_path(self, input_type: str, output_type: str, exclusive: set = None) -> list:
        """
        Find the shortest paths from input_type to output_type in the transfer matrix.
        Args:
            input_type: Input type
            output_type: Output type

        Returns:
            A list of tool chains that can convert the input_type to output_type.
        """
        assert input_type != output_type, f"input type and output type are the same: {input_type}"

        if input_type not in self.transfer_matrix:
            return []
        
        # If the input type can be converted to the output type directly
        if output_type in self.transfer_matrix[input_type]:
            return [[tool] for tool in self.transfer_matrix[input_type][output_type]]
        
        else:
            if exclusive is None:
                exclusive = set()
            new_exclusive = exclusive.union({input_type})
            
            shortest_paths = []
            for available_output_type, tools in self.transfer_matrix[input_type].items():
                # If the output type is not in the exclusive list
                if available_output_type not in new_exclusive:
                    # If the output type can be converted to the target output type
                    paths = self.find_path(available_output_type, output_type, new_exclusive)
                    if paths != []:
                        paths = [[tool] + path for tool in tools for path in paths]
                        shortest_paths.extend(paths)
            
            if shortest_paths:
                # Filter the paths to keep the shortest ones
                min_length = min([len(path) for path in shortest_paths])
                shortest_paths = [path for path in shortest_paths if len(path) == min_length]
            
            return shortest_paths
    
    