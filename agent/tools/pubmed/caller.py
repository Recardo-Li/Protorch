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
class Pubmed(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/pubmed", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, keywords, 
                 max_papers = 3, 
                 start_date = (datetime.datetime.today() - datetime.timedelta(days=3*365)).strftime('%Y-%m-%d'), 
                 end_date = datetime.datetime.today().strftime('%Y-%m-%d')) -> dict:
        
        start_time = datetime.datetime.now()
        
        cmd_args = {
            "keywords": keywords,
            "max_papers": max_papers,
            "start_date": start_date,
            "end_date": end_date,
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
                res = ast.literal_eval(content)
            spend_time = (datetime.datetime.now() - start_time).total_seconds()
            if len(res) == 0:
                return {"error": "No result found"}
            return {"search_result": res, "paper_count": len(res), "duration": spend_time}

        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    pubmed = Pubmed()
    
    input_args = {
        "keywords": "protein",
    }

    for obs in pubmed.mp_run(**input_args):
        os.system("clear")
        print(obs)
        # pubmed.terminate()
    