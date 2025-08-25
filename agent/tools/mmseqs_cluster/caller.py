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
class MMSeqsCluster(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/mmseqs_cluster", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, sequence_path, identity=0.5) -> dict:
        sequence_path = f"{self.out_dir}/{sequence_path}"
        
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        save_dir = f"{self.out_dir}/mmseqs_cluster/{now}"
        os.makedirs(save_dir, exist_ok=True)
        
        mmseqs_path = f'{ROOT_DIR}/{self.config["bin"]}'
        
        script_path = f'{BASE_DIR}/{self.config["script"]}'

        result_path = f"{save_dir}/{os.path.splitext(os.path.basename(sequence_path))[0]}_cluster{str(identity*100)}.fasta"

        script_args = [mmseqs_path, sequence_path, result_path, str(identity)]
        
        cmd = [f"cd {ROOT_DIR} && "]+ [script_path] + script_args
        cmd = " ".join(cmd)
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)
            with open(result_path) as r:
                contents = r.readlines()
                results = [1 if content.startswith(">") else 0 for content in contents]
                results_num = sum(results)
            spend_time = (datetime.datetime.now() - start).total_seconds()
            return {"sequence_path": result_path[len(self.out_dir)+1:], "results_num": results_num, "duration": spend_time}
        
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    mmseqs_cluster = MMSeqsCluster(BASE_DIR)
    
    input_args = {
        "sequence_path": "example/human_FP.fasta",
    }

    for obs in mmseqs_cluster.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # mmseqs_cluster.terminate()
    