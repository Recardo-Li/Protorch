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

class TuneCaller(BaseTool):
    def __init__(self, tool_name: str, **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            # out_dir=f"{BASE_DIR}",
            **kwargs
        )
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.tool_name = tool_name
