import shlex
import sys
import time

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch
import json_repair

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool


torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class UniprotFetchByID(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/uniprot_fetch_byid", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "uniprot_fetch_byid"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.tool_name = tool_name
        
    def __call__(self, uniprot_id, subsection="Function") -> dict:
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M")
        os.makedirs(f"{self.out_dir}/uniprot_fetch_byid/{now}", exist_ok=True)
        
        answers_template = f'{BASE_DIR}/{self.config["answers_template"]}'
        paragraph2sentence = f'{BASE_DIR}/{self.config["paragraph2sentence"]}'
        paraphrase = f'{BASE_DIR}/{self.config["paraphrase"]}'

        if subsection is not None:
            cmd_args = {
                "id": uniprot_id,
                "save_dir": f"{self.out_dir}/uniprot_fetch_byid/{now}",
                "subsection": subsection,
                "answers_template": answers_template,
                "paragraph2sentence": paragraph2sentence,
                "paraphrase": paraphrase,
            }
        else:
            cmd_args = {
                "id": uniprot_id,
                "save_dir": f"{self.out_dir}/uniprot_fetch_byid/{now}",
            }
        
        cmd_parts = [f"{self.config['python']} {BASE_DIR}/command.py"]
        for key, value in cmd_args.items():
            cmd_parts.append(f"--{key}")
            # Use shlex.quote() to handle spaces, quotes, and other special characters.
            # It's good practice to cast value to string.
            cmd_parts.append(shlex.quote(str(value)))
        
        cmd_parts.append(f"> {self.log_path} 2>&1")
        cmd = " ".join(cmd_parts)
        
        try:
            os.system(cmd)
            
            with open(self.log_path, "r") as f:
                line_start = "Uniprot items for"
                lines = f.readlines()
                for idx, line in enumerate(lines):
                    if line_start in line:
                        result_lines = lines[idx + 1:]
                        break
                else:
                    result = None
                result_str = "".join(result_lines)
                result_str = result_str.replace(self.out_dir + '/', "")
                return json_repair.loads(result_str)
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    uniprot_fetch_byid = UniprotFetchByID(BASE_DIR)
    
    input_args = {
        "uniprot_id": "P0DTC2",
        "subsection": "Domains"
    }

    for obs in uniprot_fetch_byid.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # uniprot_fetch_sequence.terminate()
    