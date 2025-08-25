import os
import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import torch

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)

HUGGINGFACE_ROOT = "/home/public/huggingface/"

class SaProtCaller(BaseTool):
    def __init__(self, tool_name: str, **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=f"{ROOT_DIR}/outputs/{tool_name}",
            **kwargs
        )
        self.config["example_output"] = self.config["example_output"][tool_name]
        
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.tool_name = tool_name
    
    def model_config(self, task_name: str):
        base_config = {
            "model_py_path": self.config[self.tool_name][task_name]["model_path"],
            "huggingface_path": HUGGINGFACE_ROOT +self.config[self.tool_name][task_name]["huggingface_path"]
        }
        if "lora_adaptor" in self.config[self.tool_name][task_name]:
            base_config["lora_adaptor"] = HUGGINGFACE_ROOT +self.config[self.tool_name][task_name]["lora_adaptor"]
        if "label_dict" in self.config[self.tool_name][task_name]:
            base_config["label_dict"] = self.config[self.tool_name][task_name]["label_dict"]
        if "num_labels" in self.config[self.tool_name][task_name]:
            base_config["num_labels"] = self.config[self.tool_name][task_name]["num_labels"]
        return base_config