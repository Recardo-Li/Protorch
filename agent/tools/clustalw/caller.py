import shlex
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
class Clustalw(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/clustalw", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, sequence_path) -> dict:
        sequence_path = f"{self.out_dir}/{sequence_path}"
        
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        
        clustalw_path = f"{ROOT_DIR}/{self.config['clustalw2']}"
            
        script_path = f"{BASE_DIR}/cmd.sh"

        result_path = f"{self.out_dir}/clustalw/{now}/{os.path.splitext(os.path.basename(sequence_path))[0]}.aln"
        os.makedirs(os.path.dirname(result_path), exist_ok=True)

        script_args = [clustalw_path, sequence_path, result_path]

        cmd =  [f"cd {ROOT_DIR} && "]+[script_path] + [shlex.quote(str(value)) for value in script_args]
        cmd = " ".join(cmd)
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)  
        
            spend_time = (datetime.datetime.now() - start).total_seconds()
            
            # if run successfully, check the result file
            if os.path.exists(result_path):
                with open(result_path, "r") as r:
                    contents = r.readlines() 
                    msas = [content for content in contents if "|" in content] 
                    results_num = len(msas)
                    
                alignment_score = None    
                with open(self.log_path, "r") as r:
                    contents = r.readlines() 
                    for i, line in enumerate(contents):
                        if "Alignment Score" in line:
                            alignment_score = float(line.replace("Alignment Score", "").strip())
                
                return {"protein_alignment": result_path[len(self.out_dir)+1:],
                        "results_num": results_num, "alignment_score": alignment_score, "duration": spend_time}
            
            else:
                return {"error": "Failed to run clustalw"}
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    clustalw = Clustalw(BASE_DIR)
    
    input_args = {
        "sequence_path": "example/human_FP.fasta",
    }

    for obs in clustalw.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # clustalw.terminate()
    