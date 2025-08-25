import sys
import time

import pandas as pd

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
class ProteinMPNN(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/proteinmpnn", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, protein_structure, chains='A', homooligomer=False, fix_pos=None, inverse=False, rm_aa=None, num_seqs=32, sampling_temp=0.1, model_name="v_48_002") -> dict:
        protein_structure = f"{self.out_dir}/{protein_structure}"
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M")
        save_dir = f"{self.out_dir}/proteinmpnn/{now}"
        os.makedirs(save_dir, exist_ok=True)
        cmd_args = {
            "pdb_path": protein_structure,
            "chains": chains,
            "out_dir": save_dir,
            "homooligomer": homooligomer,
            "inverse": inverse,
            "num_seqs": num_seqs,
            "sampling_temp": sampling_temp,
            "model_name": model_name
        }
        
        if fix_pos is not None:
            cmd_args["fix_pos"] = fix_pos
        
        if rm_aa is not None:
            cmd_args["protein_sequence"] = rm_aa
        
        # Call the ESMFold model
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            cmd += f" --{k} {v}"
        
        print(cmd)
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)  

            if os.path.exists(f"{save_dir}/mpnn_results.csv"):
                result_df = pd.read_csv(f"{save_dir}/mpnn_results.csv")
            else:
                return {"error": "ProteinMPNN failed. Please check the log file."}
            
            best_score = result_df["score"][0]
            best_seq = result_df["protein_sequence"][0]
            
            for i, row in result_df.iterrows():
                if row["score"] > best_score:
                    best_score = row["score"]
                    best_seq = row["protein_sequence"]
            
            return {
                "best_sequence": best_seq,
                "full_result": f"{save_dir[len(self.out_dir)+1:]}/mpnn_results.csv",
                "full_fasta": f"{save_dir[len(self.out_dir)+1:]}/designs.fasta",
                "best_score": best_score
            }
            
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    proteinmpnn = ProteinMPNN(BASE_DIR)
    
    input_args = {
        "protein_structure": "example/6z4g.cif"
    }

    for obs in proteinmpnn.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # proteinmpnn.terminate()
    