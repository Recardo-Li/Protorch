import sys
import time

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch
import numpy as np

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool


torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class Foldseek(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/foldseek", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, pdb_path) -> dict:
        pdb_path = f"{self.out_dir}/{pdb_path}"
        
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        os.makedirs(f"{self.out_dir}/foldseek/{now}", exist_ok=True)
        
        foldseek_path = f'{ROOT_DIR}/{self.config["bin"]}'
        
        script_path = f'{BASE_DIR}/{self.config["script"]}'

        result_path = f"{self.out_dir}/foldseek/{now}/{os.path.splitext(os.path.basename(pdb_path))[0]}.txt"

        script_args = [foldseek_path, pdb_path, result_path]
        
        cmd = [f"cd {ROOT_DIR} && "]+ [script_path] + script_args
        cmd = " ".join(cmd)
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)
        except Exception as e:
            return {"error": str(e)}
        if os.path.exists(result_path):
            with open(result_path, "r") as f:
                content = f.read()
            chain_strs = content.split('\n')
            multi_chain = len(chain_strs) > 1
            
            result = {}
            
            for chain_str in chain_strs:
                if not chain_str.strip():
                    continue
                sequence = chain_str.split('\t')[2].lower()
                evalues = [float(evalue) for evalue in chain_str.split('\t')[3].split(",")]
                avg_evalue = sum(evalues)/len(evalues)
                variance = float(np.var(evalues))
                if multi_chain:
                    chain_id = chain_str.split('\t')[0].split(' ')[0].split("_")[-1]
                    result[chain_id] = {
                        "foldseek_sequence": sequence,
                        "avg_evalue": avg_evalue,
                        "variance": variance
                    }
                else:
                    result = {
                        "foldseek_sequence": sequence,
                        "avg_evalue": avg_evalue,
                        "variance": variance
                    }
            
            spend_time = (datetime.datetime.now() - start).total_seconds()
            result["duration"] = spend_time
            return result
        else:
            return {"error": "Foldseek encountered an error. Please check your inputs and options."}
        



if __name__ == '__main__':
    # Test
    foldseek = Foldseek(BASE_DIR)
    
    input_args = {
        "pdb_path": "example/example_1.pdb",
    }

    for obs in foldseek.mp_run(**input_args):
        # os.system("clear")
        print(obs)

        # foldseek.terminate()
    