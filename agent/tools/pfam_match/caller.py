import sys
import time
import ast
ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool
import shlex

torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class Pfam_match(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/pfam_match", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, uniprot_id) -> dict:
        start = datetime.datetime.now()

        cmd_args = {
            "uniprot_id": uniprot_id,
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
            return {"search_result": res, "duration": spend_time}
        
        except Exception as e:
            return {"error": str(e)}

if __name__ == '__main__':
    # Test
    pfam_match = Pfam_match()
    
    input_args = {
        "uniprot_id": "XX",
    }

    for obs in pfam_match.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # pfam_match.terminate()
    