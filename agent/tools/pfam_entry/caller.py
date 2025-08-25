import sys
import time

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch
import ast
from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool
import shlex

torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class Pfam_entry(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/pfam_entry", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, family_id) -> dict:
        start = datetime.datetime.now()
        
        cmd_args = {
            "family_id": family_id,
        }
        
        # Call the ESMFold model
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            if isinstance(v, str):
                v = shlex.quote(v)
            cmd += f" --{k} {v}"
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
    
        try:
            os.system(cmd)  

            with open(self.log_path, "r") as r:
                content = r.read()  
                res = ast.literal_eval(content)
            spend_time = (datetime.datetime.now() - start).total_seconds()
            result = res
            result.update({
                "duration": spend_time,
            })
            return result

        except Exception as e:
            return {"error": str(e)}
        

if __name__ == '__main__':
    # Test
    pfam_entry = Pfam_entry()
    
    input_args = {
        "family_id": "PF00085",
    }

    for obs in pfam_entry.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # pfam_entry.terminate()
    