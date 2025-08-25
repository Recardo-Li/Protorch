import os
import sys
import json


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
class SaProtPairInferenceClassificationCaller(SaProtCaller):
    def __init__(self, **kwargs):
        super(SaProtCaller, self).__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=f"{ROOT_DIR}/outputs/saprot_tuned_inference_pair_classification",
            **kwargs
        )
        for doc in self.config["document"]:
            if doc["tool_name"] == "saprot_tuned_inference_pair_classification":
                self.config["document"] = doc
                break
        self.tool_name = "saprot_tuned_inference_pair_classification"

    def __call__(self, protein1_sequence, protein2_sequence, num_labels, model_dir, structure1_path=None, structure2_path=None) -> dict:
        model_dir = f"{self.out_dir}/{model_dir}"
        
        chain = "A"
        task_type = "saprot_pair_classification"
        
        with open(f"{model_dir}/adapter_config.json", "r") as r:
            adapter_config = json.load(r)
        cmd_args = {
            "model_py_path": f"{task_type}_model",
            "huggingface_path": adapter_config["base_model_name_or_path"],
            "specific_task": model_dir
        }
        cmd_args["num_labels"] = num_labels
            
        if structure1_path is not None:
            sa_seq1 = get_struc_seq(
                self.config["foldseek"],
                structure1_path
            )[chain][-1]
        else:
            sa_seq1 = ""
            for aa in protein1_sequence:
                sa_seq1 += aa + "#"
        cmd_args["sa_seq1"] = sa_seq1
        
        if structure2_path is not None:
            sa_seq2 = get_struc_seq(
                self.config["foldseek"],
                structure2_path
            )[chain][-1]
        else:
            sa_seq2 = ""
            for aa in protein2_sequence:
                sa_seq2 += aa + "#"
        cmd_args["sa_seq2"] = sa_seq2
        
        
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            cmd += f" --{k} '{v}'"
        
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
    caller = SaProtPairInferenceClassificationCaller()
    
    input_args = {
        "protein1_sequence": "AAAAAAAAAA",
        "protein2_sequence": "AAAAAAAAAA",
        "task_type": "saprot_pair_regression",
        "model_dir": "/root/ProtAgent/tmp/test/pair_regression/2025-02-11_13:26:18/[EXAMPLE][Pair AA][Regression]",
    }

    for obs in caller.mp_run(**input_args):
        os.system("clear")
        
        print(obs)