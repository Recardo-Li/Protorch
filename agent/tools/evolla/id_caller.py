import sys
import time

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool


torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class EvollaId(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/evolla_chat_byid", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "evolla_chat_byid"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.tool_name = tool_name
    
    def __call__(self, question, uniprot_id) -> dict:
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M")
        os.makedirs(f"{self.out_dir}/evolla/{now}", exist_ok=True)
        
        cmd_args = {
            "question": question,
            "uniprot_id":uniprot_id,
            "tmp_pdb_dir": f"{self.out_dir}/evolla/{now}",
            "esmfold_path": f"{ROOT_DIR}/{self.config['esmfold_path']}",
            "foldseek_path": f"{ROOT_DIR}/{self.config['foldseek_path']}",
        }
        
        # Call the ESMFold model
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            cmd += f" --{k} '{v}'"
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)
            
            ready = False
            answer = ""
            with open(self.log_path, "r") as f:
                for line in f.readlines():
                    if ready:
                        answer += line + "\n"
                    if "Loaded as API:" in line:
                        ready = True
            
            return {"answer": answer}
        except Exception as e:
            return {"error": str(e)}

if __name__ == '__main__':
    # Test
    protein_chat_byid = EvollaId()
    
    input_args = {
        "question": "What is the function of this protein?",
        "uniprot_id": "P06213",
    }

    for obs in protein_chat_byid.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # protein_chat_byid.terminate()
    