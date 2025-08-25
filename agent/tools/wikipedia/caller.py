import re
import sys
import time

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch
import ast
from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool
import shlex

torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class Wikipedia(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/wikipedia", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, query, max_items = 3) -> dict:
        
        start_time = datetime.datetime.now()
        
        cmd_args = {
            "query": query,
            "max_items": max_items,
            "proxy": self.config.get("proxy", None),
        }
        
        # Call the ESMFold model
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            if isinstance(v, str):
                v = shlex.quote(v)
            cmd += f" --{k} {v}"
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)  
        
            with open(self.log_path, "r") as r:
                content = r.read()
                try:
                    # Get everything AFTER '--- Final Results ---'
                    results_block = content.split("--- Final Results ---")[1]
                    # Get everything BEFORE the final '---------------------'
                    results_block = results_block.split("---------------------")[0]
                except IndexError:
                    print("Error: Could not find '--- Final Results ---' markers in the log content.")
                    return {"error": "Log format is incorrect; result markers not found."}
            
            pattern = re.compile(
                r"Title:\s*(.*?)\n"          # Capture group 1: Title
                r"\s*URL:\s*(.*?)\n"         # Capture group 2: URL
                r"\s*Summary:\s*(.*?)"       # Capture group 3: Summary
                r"(?=\n\nResult \d+:|\Z)",   # Lookahead for the next result or end of string
                re.DOTALL | re.MULTILINE
            )
            
            matches = pattern.findall(results_block)

            if not matches:
                print("Error: Found the result markers, but could not parse any individual result entries.")
                return {"error": "No result entries found within the result block."}
            
            final_results = []
            for match in matches:
                # The .strip() is important to remove any leading/trailing whitespace
                # from the captured strings.
                result_dict = {
                    'title': match[0].strip(),
                    'url': match[1].strip(),
                    'summary': match[2].strip()
                }
                final_results.append(result_dict)
                    
            spend_time = (datetime.datetime.now() - start_time).total_seconds()
            return {"search_result": final_results, "duration": spend_time}

        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    wikipedia = Wikipedia(BASE_DIR)
    
    input_args = {
        "query": "@#$!@$#",
        "max_items": 3,
    }

    for obs in wikipedia.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # wikipedia.terminate()
    