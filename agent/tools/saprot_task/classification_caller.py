import os
import sys


ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import torch

from utils.foldseek_util import get_struc_seq
from agent.tools.saprot_task.saprot_caller import SaProtCaller
from agent.tools.register import register_tool

torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class SaProtClassificationCaller(SaProtCaller):
    def __init__(self, **kwargs):
        super().__init__("saprot_classification", **kwargs)

    def __call__(self, protein_sequence, specific_task, structure_path=None) -> dict:
        chain = "A"
        cmd_args = self.model_config(specific_task)
        if structure_path is not None:
            sa_seq = get_struc_seq(
                self.config["foldseek"],
                structure_path
            )[chain][-1]
        else:
            sa_seq = ""
            for aa in protein_sequence:
                sa_seq += aa + "#"
        cmd_args["sa_seq"] = sa_seq
        
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            cmd += f" --{k} {v}"
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        try:
            os.system(cmd)
        
            with open(self.log_path, "r") as r:
                for line in r:
                    if line.startswith("Prediction complete. Result is "):
                        prediction = line.split("Prediction complete. Result is ")[1].strip()
                        break
            return {"pred": prediction}
        except Exception as e:
            return {"error": str(e)}
if __name__ == "__main__":
    caller = SaProtClassificationCaller()
    
    input_args = {
        "protein_sequence": "AAAAAAAAAA",
        "specific_task": "AVIDa-SARS-CoV-2-Alpha"
    }

    for obs in caller.mp_run(**input_args):
        os.system("clear")
        
        print(obs)