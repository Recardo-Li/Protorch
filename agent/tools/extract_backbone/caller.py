import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(__file__)

@register_tool
class Extractbackbone(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/extract_backbone", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, structure_file) -> dict:
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        os.makedirs(f"{self.out_dir}/extract_backbone/{now}", exist_ok=True)
        
        script_path = f'{BASE_DIR}/command.py'
        
        # Validate required parameters
        if not structure_file:
            return {"error": f"structure_file parameter is required"}
        
        # Build command arguments
        script_args = []
        # Convert relative path to absolute path based on BASE_DIR
        if not os.path.isabs(structure_file):
            abs_structure_file = os.path.join(self.out_dir, structure_file)
        else:
            abs_structure_file = structure_file
        script_args.extend(['--structure_path', abs_structure_file])
        
        cmd = ['/home/public/miniconda3/envs/protagent_backbone/bin/python', script_path] + script_args
        cmd_str = " ".join(cmd)
        
        # Redirect the stdout and stderr to a log file
        cmd_str += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd_str)
        except Exception as e:
            return {"error": str(e)}
        
        # Parse results and return
        spend_time = (datetime.datetime.now() - start).total_seconds()
        
        # Read log file for parsing output
        try:
            with open(self.log_path, "r") as f:
                output = f.read()
        except:
            output = ""
        
        # Process results according to config
        result = {}
        
        # Add return values from config
        # Extract output_path from script output
        import re
        output_match = re.search(r'Backbone structure saved to: (.+)', output)
        if output_match:
            output_path = output_match.group(1)
            # Convert to relative path
            if output_path.startswith(self.out_dir):
                result["output_path"] = output_path[len(self.out_dir)+1:]
            else:
                result["output_path"] = output_path
        else:
            result["output_path"] = "output_not_found"
        result["duration"] = spend_time
        
        return result

if __name__ == '__main__':
    tool = Extractbackbone()
    
    input_args = {
        "structure_file": "example/1A2B.pdb",
    }

    for obs in tool.mp_run(**input_args):
        os.system("clear")
        print(obs)
