import shlex
import sys
import time

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch
import pandas as pd

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool


torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class Pinal(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/pinal", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, input_text, design_num=5) -> dict:
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M")
        save_dir = f"{self.out_dir}/pinal/{now}"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        save_path = f"{save_dir}/pinal_results.csv"
        fasta_path = f"{save_dir}/designs.fasta"
        
        
        cmd_args = {
            "input_text": input_text,
            "design_num": design_num,
            "save_dir": save_dir
        }
        
        cmd_parts = [f"{self.config['python']} {BASE_DIR}/command.py"]
        for key, value in cmd_args.items():
            cmd_parts.append(f"--{key}")
            # Use shlex.quote() to handle spaces, quotes, and other special characters.
            # It's good practice to cast value to string.
            cmd_parts.append(shlex.quote(str(value)))
        
        cmd_parts.append(f"> {self.log_path} 2>&1")
        cmd = " ".join(cmd_parts)
        
        try:
            os.system(cmd)  
        
            if os.path.exists(save_path):
                result_df = pd.read_csv(save_path)
                max_logp = max(result_df["Log(p) Per Token"].tolist())
                max_protrek_score = max(result_df["Protrek Score"].tolist())
                best_sequence = result_df.loc[result_df["Log(p) Per Token"].idxmax(), "Protein Sequence"]
                
                return {"full_result": save_path[len(self.out_dir)+1:],
                        "full_fasta": fasta_path[len(self.out_dir)+1:],
                        "best_sequence": best_sequence,
                        "max_logp": max_logp, "max_protrek_score": max_protrek_score}
            else:
                return {"error": "Failed to run pinal"}
        
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    pinal = Pinal(BASE_DIR)
    
    input_args = {
        "input_text": "cytochrome c' oxidase",
        "design_num": 5
    }

    for obs in pinal.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # pinal.terminate()
    