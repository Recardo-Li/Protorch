import os
import sys
import time
from datetime import datetime

import requests

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import ast
import ast
import sys
import time

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool


BASE_DIR = os.path.dirname(__file__)


@register_tool
class GetPDB(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/pdb_entry", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, pdb_id) -> dict:
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        save_dir = f"{self.out_dir}/pdb_entry/{now}"
        
        os.makedirs(save_dir, exist_ok=True)
        
        cmd_args = {
            "pdb_id": pdb_id,
            "save_dir": save_dir
        }
        
        # Call the ESMFold model
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            cmd += f" --{k} {v}"
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        try:
            os.system(cmd)
            if not os.path.exists(f"{save_dir}/{pdb_id}.cif"):
                return {"error": f"Failed to download PDB file for ID: {pdb_id}"}
            with open(self.log_path, "r") as f:
                content = f.read()
                duration = content.split("Total time taken: ")[1]
                
            return {"pdb_file": f"{pdb_id}.cif", "duration": duration}
                
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    caller = GetPDB(BASE_DIR)
    
    input_args = {
        "pdb_id": "6z4g",
    }

    for obs in caller.mp_run(**input_args):
        os.system("clear")
        print(obs)

