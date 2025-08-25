import json
import sys

sys.path.append(".")

from data.toolset import ToolSet

class CallerType:
    FUNC=0
    SCRIPT=1

def generate_python_script(toolname: str, processor_body: str, exe_body: str, output_filename: str, callertype: CallerType,):
    """
    Generate a Python script based on the provided toolname, processor, and exe.

    Args:
    - toolname (str): The name of the tool
    - processor_body (str): The body code for the processor function
    - exe_body (str): The body code for the exe function
    - output_filename (str): The filename for the generated Python script
    """
    
    # Template for the Python class
    func_template = f"""
from data.raw_input import RawInput
from model.tool_caller.base_caller import BaseCaller
from model.model_interface import register_model

@register_model
class {toolname.capitalize()}Caller(BaseCaller):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def initialize_execution(self):
        return self.{toolname.lower()}_exe

    def initialize_processor(self):
        return self.{toolname.lower()}_processor

    def {toolname.lower()}_processor(self, input_data: RawInput, selection_result):
{processor_body}

    def {toolname.lower()}_exe(self, *args):
{exe_body}
"""

        # Template for the Python class
    script_template = f"""
from data.raw_input import RawInput
from model.tool_caller.base_caller import BaseCaller
from model.model_interface import register_model

from funchub.func_impl.bioinfo.script_runner import ScriptRunner

@register_model
class {toolname}Caller(BaseCaller):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def initialize_execution(self):
        return self.{toolname.lower()}_exe

    def initialize_processor(self):
        return self.{toolname.lower()}_processor

    def {toolname.lower()}_processor(self, input_data: RawInput, selection_result):
        {processor_body}
        self.runner = ScriptRunner(script_path, script_args)

    def {toolname.lower()}_exe(self):
        return self.runner.run()
"""

    # Write the generated script to a file
    if callertype == CallerType.FUNC:
        with open(output_filename, "w") as file:
            file.write(func_template)
    elif callertype == CallerType.SCRIPT:
        with open(output_filename, "w") as file:
            file.write(script_template)
    else:
        raise ValueError("Invalid caller type")
    
    print(f"Python script has been generated and saved as {output_filename}.")


def get_input(prompt):
    """Helper function to get input from the user."""
    return input(prompt).strip()

def add_parameter(parameter_type="required"):
    """Helper function to add a parameter to the required or optional list."""
    parameters = []
    while True:
        name = get_input(f"Enter the name of the {parameter_type} parameter (or 'done' to finish): ")
        if name.lower() == "done":
            break
        param_type = get_input(f"Enter the type of the parameter '{name}': ")
        description = get_input(f"Enter the description for the parameter '{name}': ")

        param = {
            "name": name,
            "type": param_type,
            "description": description
        }

        if parameter_type == "optional":
            default = get_input(f"Enter the default value for the optional parameter '{name}': ")
            param["default"] = default

        parameters.append(param)
    
    return parameters

def generate_json():
    """Main function to generate the JSON structure."""
    toolname = get_input("Enter the tool name: ")
    toolname=toolname.lower()
    print(f"Generating document for {toolname}...")
    description = get_input("Enter the tool description: ")

    required_parameters = add_parameter(parameter_type="required")
    optional_parameters = add_parameter(parameter_type="optional")

    # Adding return values
    return_values = []
    while True:
        name = get_input("Enter the name of the return value (or 'done' to finish): ")
        if name.lower() == "done":
            break
        return_type = get_input(f"Enter the type of the return value '{name}': ")
        return_description = get_input(f"Enter the description for the return value '{name}': ")

        return_values.append({
            "name": name,
            "type": return_type,
            "description": return_description
        })

    # Creating the JSON structure
    json_data = {
        "category_name": toolname,
        "tool_name": toolname,
        "tool_description": description,
        "required_parameters": required_parameters,
        "optional_parameters": optional_parameters,
        "return_values": return_values
    }

    # Convert dictionary to JSON string
    json_string = json.dumps(json_data, indent=4)
    
    # Output JSON to file
    output_filename = f"tmp/{toolname}.json"
    with open(output_filename, "w") as json_file:
        json_file.write(json_string)
    
    print(f"{toolname}'s document has been generated and saved as {output_filename}.")
    return toolname, output_filename


def add_new_tool(processor_body: str, exe_body: str, callertype: CallerType, toolset: ToolSet):
    toolname, tmp_doc_path = generate_json()
    
    toolname=toolname.lower()
    output_caller_path = f"model/tool_caller/{toolname}_caller.py"
    generate_python_script(toolname, processor_body, exe_body, output_caller_path, callertype)
    
    toolset.add_func(tmp_doc_path, toolname, toolname)

if __name__ == "__main__":
    # Example usage

    toolname = "DataAnalyzer"
    processor_body = """
            # Example processing code
            processed_data = [x for x in input_data.data if x in selection_result]
            print(f"Processed data: {{processed_data}}")
            return processed_data
    """

    exe_body = """
            # Example execution code
            analysis_result = {{
                "count": len(args[0]),
                "mean": sum(args[0]) / len(args[0]) if args[0] else 0,
                "max": max(args[0]) if args[0] else None,
                "min": min(args[0]) if args[0] else None
            }}
            print(f"Analysis Result: {{analysis_result}}")
            return analysis_result
    """

    add_new_tool(processor_body, exe_body, CallerType.FUNC, ToolSet("funchub"))
