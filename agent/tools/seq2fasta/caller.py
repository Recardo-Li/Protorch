import os
import shlex
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
class Seq2Fasta(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/seq2fasta", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, protein_sequence, header=">protein_sequence") -> dict:
        
        
        if ">" in header:
            name = header.split()[0][1:]
        else:
            name = header.split()[0]
        
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M")
        save_dir = f"{self.out_dir}/seq2fasta/{now}"
        os.makedirs(save_dir, exist_ok=True)
        
        cmd_args = {
            "protein_sequence": protein_sequence,
            "header": header, 
            "save_path": f"{save_dir}/{name}.fasta",
        }
        
        # Call the ESMFold model
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            if isinstance(v, str):
                v = shlex.quote(v)
            cmd += f" --{k} {v}"
        print(cmd)
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        try:
            os.system(cmd)
            if not os.path.exists(f"{save_dir}/{name}.fasta"):
                return {"error": f"Failed to save FASTA file for {name}"}
                
            return {"fasta_file": f"seq2fasta/{now}/{name}.fasta"}
                
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    caller = Seq2Fasta(BASE_DIR)
    
    input_args = {
        "protein_sequence": "MKTAYIAKQRQ ISFVKSHFSRQDILDLW",
        "header": ">example_sequence"
    }

    for obs in caller.mp_run(**input_args):
        os.system("clear")
        print(obs)

