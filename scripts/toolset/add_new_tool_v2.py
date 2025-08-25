import json
import sys
import yaml
import os
import shutil
from pathlib import Path

sys.path.append(".")

from enum import IntEnum

class ScriptType(IntEnum):
    PYTHON = 0
    SHELL = 1

def get_input(prompt):
    """Helper function to get input from the user."""
    return input(prompt).strip()

def detect_script_type(script_path: str) -> ScriptType:
    """Detect if the script is Python or shell based on file extension."""
    ext = os.path.splitext(script_path)[1].lower()
    if ext == '.py':
        return ScriptType.PYTHON
    elif ext in ['.sh', '.bash']:
        return ScriptType.SHELL
    else:
        # Try to detect from shebang
        try:
            with open(script_path, 'r') as f:
                first_line = f.readline().strip()
                if first_line.startswith('#!') and 'python' in first_line:
                    return ScriptType.PYTHON
                elif first_line.startswith('#!') and ('bash' in first_line or 'sh' in first_line):
                    return ScriptType.SHELL
        except:
            pass
        
        # Default to shell if uncertain
        return ScriptType.SHELL

def add_parameter(parameter_type="required"):
    """Helper function to add a parameter to the required or optional list."""
    parameters = []
    while True:
        name = get_input(f"Enter the name of the {parameter_type} parameter (or 'done' to finish): ")
        if name.lower() == "done":
            break
        param_type = get_input(f"Enter the type of the parameter '{name}' (TEXT/INTEGER/FLOAT/BOOLEAN/PATH/LIST): ")
        detailed_type = get_input(f"Enter the detailed type of the parameter '{name}': ")
        description = get_input(f"Enter the description for the parameter '{name}': ")

        param = {
            "name": name,
            "type": param_type.upper(),
            "detailed_type": detailed_type.upper(),
            "description": description
        }

        if parameter_type == "optional":
            default = get_input(f"Enter the default value for the optional parameter '{name}' (or 'null' for None): ")
            if default.lower() == "null" or not default:
                param["default"] = "null"
            else:
                param["default"] = default

        parameters.append(param)
    
    return parameters

def add_return_values():
    """Helper function to add return values."""
    return_values = []
    while True:
        name = get_input("Enter the name of the return value (or 'done' to finish): ")
        if name.lower() == "done":
            break
        return_type = get_input(f"Enter the type of the return value '{name}' (TEXT/INTEGER/FLOAT/BOOLEAN/DICT/LIST): ")
        detailed_type = get_input(f"Enter the detailed type of the return value '{name}': ")
        description = get_input(f"Enter the description for the return value '{name}': ")

        return_values.append({
            "name": name,
            "type": return_type.upper(),
            "detailed_type": detailed_type.upper(),
            "description": description
        })
    
    return return_values

def add_return_scores():
    """Helper function to add return scores."""
    return_scores = []
    while True:
        name = get_input("Enter the name of the return score (or 'done' to finish): ")
        if name.lower() == "done":
            break
        description = get_input(f"Enter the description for the return score '{name}': ")

        return_scores.append({
            "name": name,
            "description": description
        })
    
    return return_scores

def generate_config(toolname: str):
    """Generate the configuration YAML file."""
    print(f"Generating config for {toolname}...")
    
    category_name = get_input("Enter the category name (e.g., Structure, Analysis, Search): ")
    description = get_input("Enter the tool description: ")

    required_parameters = add_parameter(parameter_type="required")
    optional_parameters = add_parameter(parameter_type="optional")
    return_values = add_return_values()
    return_scores = add_return_scores()

    # Creating the YAML structure
    yaml_data = {
        "document": {
            "category_name": category_name,
            "tool_name": toolname,
            "tool_description": description,
            "required_parameters": required_parameters,
            "optional_parameters": optional_parameters,
            "return_values": return_values,
            "return_scores": return_scores
        }
    }

    return yaml_data

def generate_caller_for_script(toolname: str, script_filename: str, script_type: ScriptType, required_params: list, optional_params: list, return_values: list, return_scores: list) -> str:
    """Generate caller.py for script execution."""
    
    # Generate function parameters
    func_params = []
    for param in required_params:
        func_params.append(f"{param['name']}")
    for param in optional_params:
        default_val = param.get('default', 'null')
        if default_val == 'null':
            default_val = 'None'
        func_params.append(f"{param['name']}={default_val}")
    
    func_signature = ', '.join(func_params)
    
    # Generate parameter processing
    param_processing = ""
    for param in required_params:
        param_name = param['name']
        param_processing += f"""
        if not {param_name}:
            return {{"error": f"{param_name} parameter is required"}}"""
    
    # Generate parameter handling
    param_handling = ""
    for param in required_params + optional_params:
        param_name = param['name']
        param_type = param.get('type', 'TEXT')
        
        if param in optional_params:
            if param_type == 'PATH':
                param_handling += f"""
        if {param_name} is not None:
            # Convert relative path to absolute path for PATH parameters
            if not os.path.isabs({param_name}):
                abs_{param_name} = os.path.join(BASE_DIR, {param_name})
            else:
                abs_{param_name} = {param_name}
            script_args.extend(['--{param_name}', abs_{param_name}])"""
            else:
                param_handling += f"""
        if {param_name} is not None:
            script_args.extend(['--{param_name}', str({param_name})])"""
        else:
            if param_type == 'PATH':
                param_handling += f"""
        # Convert relative path to absolute path for PATH parameters
        if not os.path.isabs({param_name}):
            abs_{param_name} = os.path.join(BASE_DIR, {param_name})
        else:
            abs_{param_name} = {param_name}
        script_args.extend(['--{param_name}', abs_{param_name}])"""
            else:
                param_handling += f"""
        script_args.extend(['--{param_name}', str({param_name})])"""
    
    # Generate script execution command
    if script_type == ScriptType.PYTHON:
        script_executor = "'/home/public/miniconda3/envs/protagent_backbone/bin/python'"
    else:
        script_executor = "'bash'"

    # Generate return value processing based on config
    result_processing = """
        result = {}
        
        # Add return values from config"""
    
    for return_val in return_values:
        val_name = return_val['name']
        if return_val['type'] == 'PATH':
            result_processing += f"""
        # TODO: Extract {val_name} from script output or determine output path
        result["{val_name}"] = "path_to_output_file"  # Modify this based on your script's actual output"""
        else:
            result_processing += f"""
        # TODO: Extract {val_name} from script output
        result["{val_name}"] = "extracted_value"  # Modify this based on your script's actual output"""
    
    for return_score in return_scores:
        score_name = return_score['name']
        if score_name == 'duration':
            result_processing += f"""
        result["{score_name}"] = spend_time"""
        else:
            result_processing += f"""
        # TODO: Extract {score_name} from script output
        result["{score_name}"] = 0.0  # Modify this based on your script's actual output"""
    
    result_processing += """
        
        return result"""

    # Generate example parameters
    example_params = ""
    for i, param in enumerate(required_params):
        example_params += f'\n        "{param["name"]}": "example_value_{i+1}",'
    
    class_name = toolname.capitalize().replace('_', '')

    caller_template = f'''import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(__file__)

@register_tool
class {class_name}(BaseTool):
    def __init__(self, out_dir: str = f"{{ROOT_DIR}}/outputs/{toolname}", **kwargs):
        super().__init__(
            config_path=f"{{BASE_DIR}}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, {func_signature}) -> dict:
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        os.makedirs(f"{{self.out_dir}}/{toolname}/{{now}}", exist_ok=True)
        
        script_path = f'{{BASE_DIR}}/{script_filename}'
        
        # Validate required parameters{param_processing}
        
        # Build command arguments
        script_args = []{param_handling}
        
        cmd = [{script_executor}, script_path] + script_args
        cmd_str = " ".join(cmd)
        
        # Redirect the stdout and stderr to a log file
        cmd_str += f" > {{self.log_path}} 2>&1"
        
        try:
            os.system(cmd_str)
        except Exception as e:
            return {{"error": str(e)}}
        
        # Parse results and return
        spend_time = (datetime.datetime.now() - start).total_seconds()
        
        # Read log file for parsing output
        try:
            with open(self.log_path, "r") as f:
                output = f.read()
        except:
            output = ""
        
        # Process results according to config{result_processing}

if __name__ == '__main__':
    tool = {class_name}()
    
    input_args = {{{example_params}
    }}

    for obs in tool.mp_run(**input_args):
        os.system("clear")
        print(obs)
'''
    
    return caller_template

def update_tool_manager_config(tool_name: str):
    """Update tool manager config to include new tool"""
    config_path = "agent/tools/tool_manager_config.yaml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        tools_start = -1
        tools_end = -1
        
        for i, line in enumerate(lines):
            if line.strip() == 'tools: [':
                tools_start = i
            elif tools_start != -1 and line.strip() == ']':
                tools_end = i
                break
        
        if tools_start != -1 and tools_end != -1:
            insert_line = f"    {tool_name}.caller,"
            lines.insert(tools_end, insert_line)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            print(f"Updated tool_manager_config.yaml with {tool_name}")
            
    except Exception as e:
        print(f"Warning: Could not update tool_manager_config.yaml: {e}")

def create_tool_from_script():
    """Main function to create a tool from an existing script."""
    # Get script information
    script_path = get_input("Enter the full path to your script file: ")
    if not os.path.exists(script_path):
        print(f"Error: Script file not found: {script_path}")
        return
    
    toolname = get_input("Enter the tool name: ")
    toolname = toolname.lower().replace(" ", "_")
    
    # Detect script type
    script_type = detect_script_type(script_path)
    script_filename = os.path.basename(script_path)
    
    print(f"Detected script type: {'Python' if script_type == ScriptType.PYTHON else 'Shell'}")
    print(f"Script filename: {script_filename}")
    
    # Create tool directory
    tool_dir = f"agent/tools/{toolname}"
    
    # Check if tool directory already exists and handle it
    if os.path.exists(tool_dir):
        print(f"Warning: Tool directory '{tool_dir}' already exists!")
        choice = get_input("Do you want to overwrite it? (y/n): ")
        if choice.lower() != 'y':
            print("Tool creation cancelled.")
            return
        print("Overwriting existing tool...")
    
    os.makedirs(tool_dir, exist_ok=True)
    
    # Copy script to tool directory (only if it's not the same file)
    dest_script_path = os.path.join(tool_dir, script_filename)
    if os.path.abspath(script_path) != os.path.abspath(dest_script_path):
        shutil.copy2(script_path, dest_script_path)
        print(f"Copied script to: {dest_script_path}")
    else:
        print(f"Script already exists at target location: {dest_script_path}")
    
    # Generate config
    config_data = generate_config(toolname)
    
    # Save config
    config_path = f"{tool_dir}/config.yaml"
    yaml_string = yaml.dump(config_data, default_flow_style=False, allow_unicode=True, indent=2)
    with open(config_path, "w") as yaml_file:
        yaml_file.write(yaml_string)
    
    # Generate caller.py
    caller_content = generate_caller_for_script(
        toolname, 
        script_filename, 
        script_type, 
        config_data['document']['required_parameters'],
        config_data['document']['optional_parameters'],
        config_data['document']['return_values'],
        config_data['document']['return_scores']
    )
    
    caller_path = f"{tool_dir}/caller.py"
    with open(caller_path, "w") as caller_file:
        caller_file.write(caller_content)
    
    # Update tool manager config
    update_tool_manager_config(toolname)
    
    print(f"Tool '{toolname}' has been successfully created!")
    print(f"Tool directory: {tool_dir}")
    print(f"Files created:")
    print(f"  - {tool_dir}/caller.py")
    print(f"  - {tool_dir}/config.yaml")
    print(f"  - {tool_dir}/{script_filename}")

if __name__ == "__main__":
    create_tool_from_script() 