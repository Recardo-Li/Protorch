import sys
import json
ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import shlex
import ast
from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool
from agent.tools.biorxiv.module import BiorxivRetriever

BASE_DIR = os.path.dirname(__file__)

@register_tool
class Biorxiv(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/biorxiv", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, keywords, 
                 max_papers = 25, 
                 start_date = (datetime.datetime.today() - datetime.timedelta(days=3*365)).strftime('%Y-%m-%d'), 
                 end_date = datetime.datetime.today().strftime('%Y-%m-%d')) -> dict:
        
        start_time = datetime.datetime.now()
        if start_date is None or len(start_date.strip()) == 0:
            start_date = (datetime.datetime.today() - datetime.timedelta(days=3*365)).strftime('%Y-%m-%d')
        
        if end_date is None or len(end_date.strip()) == 0:
            end_date = datetime.datetime.today().strftime('%Y-%m-%d')
    
        cmd_args = {
            "keywords": keywords,
            "max_papers": max_papers,
            "start_date": start_date,
            "end_date": end_date,
        }
        
        # Call the Biorxiv command
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            if isinstance(v, str):
                v = shlex.quote(v)
            cmd += f" --{k} {v}"

        cmd += f" > {self.log_path} 2>&1"

        try:
            os.system(cmd)  

            # if run successfully, check the log info
            with open(self.log_path, "r") as r:
                content = r.read()  
                res = ast.literal_eval(content) 
            spend_time = (datetime.datetime.now() - start_time).total_seconds()
            count = len(res)
            if count == 0:
                return {"error": "No papers found for the given keywords."}
            else:
                return {"paper": res, "paper_count": count,"duration": spend_time}
            
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    biorxiv = Biorxiv(BASE_DIR)
    
    input_args = {
        "keywords": "protein",
    }

    for obs in biorxiv.mp_run(**input_args):
       
        os.system("clear")
        print(obs)

        # biorxiv.terminate()
        # pass