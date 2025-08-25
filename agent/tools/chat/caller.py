import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import os

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(__file__)


@register_tool
class Chat(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/Chat", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self) -> dict:
        """
        Chat with the user without any specific tool
        """
        with open(self.log_path, "w") as w:
            pass
        return {}


if __name__ == '__main__':
    # Test
    chat = Chat()
    
    input_args = {}
    chat.run(**input_args)
