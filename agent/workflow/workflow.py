import json
import sys
from graphviz import Digraph
from typing import Dict, Any, List, Optional

from easydict import EasyDict

import json_repair

ROOT_DIR = __file__.rsplit("/", 3)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from agent.tools.base_tool import BaseTool
from agent.workflow.tool_node import ToolNode
from agent.tools.tool_manager import ToolManager
from agent.utils.constants import TOOLNODE_STATUS

class Workflow:
    """
    Manages a sequence of ToolNodes and their connections.
    """
    def __init__(self):
        self.nodes: Dict[str, ToolNode] = {}
        self.node_order: List[str] = []

    @classmethod
    def from_config(cls, config: Dict[str, Any], tool_manager:ToolManager) -> 'Workflow':
        """
        Factory method to create a Workflow from a JSON/dict configuration.
        
        Args:
            config (Dict[str, Any]): The workflow configuration.
            tool_manager (ToolManager): An instance of ToolManager to retrieve tool classes.
            
        Returns:
            An initialized Workflow instance.
        """
        print("--- Creating Workflow from configuration ---")
        workflow = cls()
        # Sort keys to ensure deterministic order (e.g., 'step_1', 'step_2')
        for node_id in sorted(config.keys()):
            node_config = config[node_id]
            if isinstance(node_config, str):
                node_config = json_repair.loads(node_config)
            tool_name = node_config.get("tool")
            if not tool_name:
                raise ValueError(f"Node '{node_id}' is missing the 'tool' key.")
            
            tool_instance = tool_manager.get_tool(tool_name)
            if not tool_instance:
                raise ValueError(f"Tool '{tool_name}' for node '{node_id}' not found in registry.")
                
            node = ToolNode(node_id=node_id, tool=tool_instance)
            
            if node_config.get("executed", "No").lower() == "yes" or node_config.get("status", "INIT").upper()=="EXECUTED":
                node.status = TOOLNODE_STATUS.EXECUTED
                node.tool_args = config[node_id].get("tool_args", {})
                node.results = config[node_id].get("results", {})
            
            if node_config.get("parameter_origins"):
                # If parameter origins are provided, set them
                node.parameter_origins = EasyDict(node_config["parameter_origins"])
            
            workflow.nodes[node_id] = node
            workflow.node_order.append(node_id)
        print("--- Workflow creation complete ---\n")
        
        return workflow

    def connect(self, upstream_node_id: str, upstream_output_name: str,
                downstream_node_id: str, downstream_input_name: str):
        """
        Connects an output of an upstream node to an input of a downstream node.
        
        This updates the 'comefrom' status of the downstream parameter.
        """
        # --- Validation ---
        if upstream_node_id not in self.nodes:
            raise KeyError(f"Upstream node '{upstream_node_id}' not found.")
        if downstream_node_id not in self.nodes:
            raise KeyError(f"Downstream node '{downstream_node_id}' not found.")
            
        upstream_node = self.nodes[upstream_node_id]
        downstream_node = self.nodes[downstream_node_id]
        
        # Validate upstream output exists
        upstream_outputs = {out['name'] for out in upstream_node.tool.config.document['return_values']}
        if upstream_output_name not in upstream_outputs:
            raise ValueError(f"Output '{upstream_output_name}' not found on tool '{upstream_node.tool.tool_name}' in node '{upstream_node_id}'.")

        # Validate downstream input exists and is not already connected
        if downstream_input_name not in downstream_node.parameter_origins:
            raise ValueError(f"Input '{downstream_input_name}' not found on tool '{downstream_node.tool.tool_name}' in node '{downstream_node_id}'.")
        
        # --- Update the downstream parameter's origin ---
        print(f"Connecting: {upstream_node_id}:{upstream_output_name} -> {downstream_node_id}:{downstream_input_name}")
        downstream_node.parameter_origins[downstream_input_name] = {
            'source': 'node_output',
            'node_id': upstream_node_id,
            'output_name': upstream_output_name
        }
        print(f"  - Parameter '{downstream_input_name}' in node '{downstream_node_id}' is now sourced from '{upstream_node_id}'.\n")

    def to_json(self) -> Dict[str, Any]:
        json_data = {}
        for node_id, node in self.nodes.items():
            json_data[node_id] = {
                'tool': node.tool.tool_name,
                'status': node.status,
                'parameter_origins': node.parameter_origins,
            }
            if node.tool_args:
                json_data[node_id]['tool_args'] = node.tool_args
            if node.results:
                json_data[node_id]['results'] = node.results
        return json_data

    def to_template(self) -> Dict[str, Any]:
        """
        Converts the workflow to a template string format.
        
        Returns:
            A string representation of the workflow configuration.
        """
        json_data = {}
        for node_id, node in self.nodes.items():
            json_data[node_id] = {
                'tool': node.tool.tool_name,
                'parameter_origins': node.parameter_origins,
            }
        
        return json_data

    def insert_nodes_before(self, tool_chain: List[BaseTool], current_node_id: str):
        '''
        When current argument pool does not contain enough information for the current node, and inserting a new tool path before this tool would successfully address this issue, insert a list of tool nodes before the current node.
        '''
        if not current_node_id.startswith("step_"):
            raise ValueError(f"Invalid node ID '{current_node_id}'. It should start with 'step_'.")
        
        wrong_step = int(current_node_id.split('_')[1])
        origin_num = len(self.node_order)
        added_num = len(tool_chain)
        
        for i in range(origin_num, wrong_step-1, -1):
            self.nodes[f'step_{i+added_num}'] = self.nodes[f'step_{i}']
        
        for i, tool_instance in enumerate(tool_chain):
            self.nodes[f'step_{wrong_step+i}'] = ToolNode(
                node_id=f'step_{wrong_step+i}',
                tool=tool_instance
            )
        
        self.node_order = [f'step_{i+1}' for i in range(origin_num + added_num)]

    def print_nodes(self):
        """
        Prints the details of all nodes in the workflow.
        """
        print("--- Workflow Nodes ---")
        for node_id, node in self.nodes.items():
            print(f"Node ID: {node_id}, Tool: {node.tool.tool_name}")
            print(f"  Status: {node.status}")
            print("  Inputs:")
            for param_name, origin in node.parameter_origins.items():
                if origin['source'] == 'default':
                    continue
                print(f"    - {param_name}: {origin['source']}")
            print("  Outputs:")
            for output in node.tool.config.document.get('return_values', []):
                print(f"    - {output['name']}")
        print("--- End of Workflow Nodes ---\n")

    def visualize(self, filename: str = 'workflow_graph', format: str = 'png') -> Optional[Digraph]:
        """
        Generates a visual representation of the workflow graph using graphviz.
        
        Args:
            filename (str): The name of the output file (without extension).
            format (str): The output format (e.g., 'png', 'svg', 'pdf').
            
        Returns:
            The graphviz Digraph object, or None if the library is not installed.
        """
        if Digraph is None:
            print("Cannot visualize: graphviz library is not installed.")
            return None
            
        dot = Digraph(comment='Workflow Graph')
        dot.attr('node', shape='box', style='rounded')
        dot.attr(rankdir='LR') # Left to Right layout

        # Add nodes to the graph
        for node_id in self.node_order:
            node = self.nodes[node_id]
            
            # Create an HTML-like label for rich node representation
            label = f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0"><TR><TD COLSPAN="2" BGCOLOR="lightblue"><b>{node.node_id}</b><BR/>({node.tool.tool_name})</TD></TR>'
            
            # Add inputs
            label += '<TR><TD COLSPAN="2" BGCOLOR="lightgrey"><i>Inputs</i></TD></TR>'
            all_params = (node.tool.config.document.get("required_parameters", []) + 
                          node.tool.config.document.get("optional_parameters", []))
            for param in all_params:
                param_name = param['name']
                origin = node.parameter_origins[param_name]
                if origin['source'] == 'default':
                    continue
                origin_str = f"<i>from {origin['source']}</i>"
                if origin['source'] == 'node_output':
                    origin_str = f"<i>from {origin['node_id']}:{origin['output_name']}</i>"
                label += f'<TR><TD ALIGN="LEFT">{param_name}</TD><TD ALIGN="LEFT">{origin_str}</TD></TR>'

            # Add outputs
            label += '<TR><TD COLSPAN="2" BGCOLOR="lightgrey"><i>Outputs</i></TD></TR>'
            for output in node.tool.config.document.get("return_values", []):
                label += f'<TR><TD COLSPAN="2" ALIGN="LEFT">{output["name"]}</TD></TR>'
            
            label += '</TABLE>>'
            dot.node(node_id, label=label)

        # Add edges based on connections
        for node_id, node in self.nodes.items():
            for origin_info in node.parameter_origins.values():
                if origin_info['source'] == 'node_output':
                    source_node_id = origin_info['node_id']
                    output_name = origin_info['output_name']
                    dot.edge(source_node_id, node_id, label=output_name)
        
        # print(f"\nRendering graph to '{filename}.{format}'...")
        # dot.render(filename, format=format, view=False, cleanup=True)
        # print("Graph rendered successfully.")
        return dot

    def get_global_io(self) -> Dict[str, Any]:
        """
        Analyzes the entire workflow to find its global inputs and outputs.
        
        - Global inputs are parameters that require user input.
        - Global outputs are node outputs that are not consumed by any other node.
        
        Returns:
            A dictionary with two keys:
            'inputs': A dict mapping node_id to a list of its user-input parameter names.
            'outputs': A list of dicts, each representing an unconsumed output.
        """
        global_inputs = {}
        all_possible_outputs = []
        consumed_outputs = set()

        # Iterate through all nodes to gather information
        for node_id, node in self.nodes.items():
            # --- Find global inputs and consumed outputs ---
            node_user_inputs = []
            for param_name, origin_info in node.parameter_origins.items():
                if origin_info['source'] == 'user_input':
                    node_user_inputs.append(param_name)
                elif origin_info['source'] == 'node_output':
                    # This parameter consumes an output, so we record it.
                    source_node = origin_info['node_id']
                    source_output = origin_info['output_name']
                    consumed_outputs.add((source_node, source_output))
            
            if node_user_inputs:
                global_inputs[node_id] = node_user_inputs
            
            # --- Find all possible outputs from this node ---
            for output_def in node.tool.config.document.get('return_values', []):
                all_possible_outputs.append({
                    'node_id': node_id,
                    'output_name': output_def['name']
                })

        # --- Determine global outputs by filtering out consumed ones ---
        global_outputs = []
        for output in all_possible_outputs:
            output_as_tuple = (output['node_id'], output['output_name'])
            if output_as_tuple not in consumed_outputs:
                global_outputs.append(output)
                
        return {
            'inputs': global_inputs,
            'outputs': global_outputs
        }


if __name__ == '__main__':
    # 1. Define the workflow structure using the provided JSON
    workflow_config_json = """
    {
        "step_1": {
            "tool": "uniprot_fetch_byid", 
            "reason": "To obtain the protein sequence and structure information for the given UniProt ID. This is necessary to define the target for binder design."
        }, 
        "step_2": {
            "tool": "rfdiffusion_binder_design", 
            "reason": "Once the structure of the target protein is obtained, this tool will be used to design a binder with specified length and binding region based on the structure."
        }, 
        "step_3": {
            "tool": "proteinmpnn", 
            "reason": "After generating a backbone structure for the binder, ProteinMPNN will be used to design the amino acid sequence that best fits the designed backbone structure."
        }, 
        "step_4": {
            "tool": "alphafold2", 
            "reason": "To refine and validate the final binder design by predicting its full 3D structure and ensuring it folds correctly when bound to the target."
        }
    }
    """
    workflow_config = json.loads(workflow_config_json)

    print("--- Protein Binder Design Workflow ---")

    # 2. Initialize the workflow from the configuration and the new tool registry
    tool_manager = ToolManager()
    my_workflow = Workflow.from_config(workflow_config, tool_manager)

    # 3. Define the data flow by connecting the nodes based on our analysis
    print("--- Connecting workflow nodes ---")
    
    # Connect UniprotFetch output to RFDiffusion input
    my_workflow.connect(
        upstream_node_id='step_1',
        upstream_output_name='protein_structure',
        downstream_node_id='step_2',
        downstream_input_name='protein_structure'
    )

    # Connect RFDiffusion output to ProteinMPNN input
    my_workflow.connect(
        upstream_node_id='step_2',
        upstream_output_name='design',
        downstream_node_id='step_3',
        downstream_input_name='protein_structure'
    )
    
    # Connect ProteinMPNN output to AlphaFold2 input
    my_workflow.connect(
        upstream_node_id='step_3',
        upstream_output_name='best_sequence',
        downstream_node_id='step_4',
        downstream_input_name='protein_sequence' # Note: the parameter name on the tool is 'binder_pdb'
    )
    
    
    # 4. Get and display the global inputs and outputs
    print("--- Analyzing Workflow Interface ---")
    workflow_io = my_workflow.get_global_io()

    print("\n[ Global Workflow Inputs ]")
    print("The following parameters must be provided by the user:")
    if not workflow_io['inputs']:
        print("- None")
    else:
        for node_id, params in workflow_io['inputs'].items():
            for param_name in params:
                print(f"- Node '{node_id}': requires input for '{param_name}'")

    print("\n[ Global Workflow Outputs ]")
    print("The following final outputs will be generated:")
    if not workflow_io['outputs']:
        print("- None")
    else:
        for output_info in workflow_io['outputs']:
            print(f"- Node '{output_info['node_id']}': produces final output '{output_info['output_name']}'")

    # 5. Visualize the final workflow graph
    # This will generate a file named 'protein_binder_design_workflow.png'
    my_workflow.visualize(filename='protein_binder_design_workflow', format='png')
