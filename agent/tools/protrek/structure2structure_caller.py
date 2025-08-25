import datetime
import os
import re
import sys

import pandas as pd

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(__file__)


@register_tool
class ProTrekStructure2Structure(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/protrek_structure2structure", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "protrek_structure2structure"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.tool_name = tool_name
        
    def __call__(self, foldseek_sequence, database="Swiss-Prot"):
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        os.makedirs(f"{self.out_dir}/protrek", exist_ok=True)
        
        cmd_args = {
            "query": foldseek_sequence,
            "database": database,
            "input_type": "structure",
            "query_type": "structure",
            "csv_path": f"{self.out_dir}/protrek/{now}-structure2structure.csv",
        }
        
        # Call the ESMFold model
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            cmd += f" --{k} '{v}'"
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)
            
            with open(cmd_args["csv_path"]) as f:
                df = pd.read_csv(f)

            spend_time = (datetime.datetime.now() - start).total_seconds()
            return {"protein_id": df.iloc[0]["Id"],
                    "foldseek_sequence": df.iloc[0]["Foldseek sequence"],
                    "protein_length": int(df.iloc[0]["Length"]),
                    "matching_score": float(df.iloc[0]["Matching score"]),
                    "duration": spend_time
                    }
        except Exception as e:
            return {"error": str(e)}

if __name__ == '__main__':
    # Test
    tool = ProTrekStructure2Structure()
    
    input_args = {
        "foldseek_sequence": "dddadcpvpvqkakevrvk",
        "database": "Swiss-Prot",
    }

    for obs in tool.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # pinal.terminate()
    