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
class SaProtInferenceTokenClassificationCaller(SaProtCaller):
    def __init__(self, **kwargs):
        super(SaProtCaller, self).__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=f"{ROOT_DIR}/output/temp",
            **kwargs
        )
        for doc in self.config["document"]:
            if doc["tool_name"] == "saprot_tuned_inference_token_classification":
                self.config["document"] = doc
                break
        self.tool_name = "saprot_tuned_inference_token_classification"

    def __call__(self, protein_sequence, num_labels, model_dir, structure_path=None) -> dict:
        model_dir = f"{self.out_dir}/{model_dir}"
        print("model_dir: ", model_dir)
        
        chain = "A"
        task_type = "saprot_token_classification"
        
        with open(f"{model_dir}/adapter_config.json", "r") as r:
            adapter_config = json.load(r)
        cmd_args = {
            "model_py_path": f"{task_type}_model",
            "huggingface_path": adapter_config["base_model_name_or_path"],
            "lora_adaptor": model_dir
        }
        cmd_args["num_labels"] = num_labels
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
                prediction = None
                for line in r:
                    if line.startswith("Prediction complete. Result is "):
                        prediction = line.split("Prediction complete. Result is ")[1].strip()
                        break
            if prediction is None:
                return {"error": "Prediction failed"}
            return {"pred": prediction}
        except Exception as e:
            return {"error": str(e)}
    
if __name__ == "__main__":
    caller = SaProtInferenceTokenClassificationCaller()
    
    input_args = {
        "protein_sequence": "AAAAAAAAAA",
        "task_type": "saprot_classification",
        "model_dir": "classification/2025-03-18_21:02:47/[EXAMPLE][Classification-2Categories]Multiple_AA_Sequences",
        "num_labels": 2
    }

    for obs in caller.mp_run(**input_args):
        # os.system("clear")
        
        print(obs)