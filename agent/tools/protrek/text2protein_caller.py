import datetime
import os
import re
import shlex
import sys

import pandas as pd

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(__file__)


@register_tool
class ProTrekText2Protein(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/protrek_text2protein", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "protrek_text2protein"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.tool_name = tool_name

    def __call__(self, protein_text, database="Swiss-Prot"):
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        os.makedirs(f"{self.out_dir}/protrek", exist_ok=True)
        
        cmd_args = {
            "query": protein_text,
            "database": database,
            "input_type": "text",
            "query_type": "sequence",
            "csv_path": f"{self.out_dir}/protrek/{now}-text2protein.csv",
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
            
            with open(cmd_args["csv_path"]) as f:
                df = pd.read_csv(f)

            spend_time = (datetime.datetime.now() - start).total_seconds()
            return {"protein_id": df.iloc[0]["Id"],
                    "protein_sequence": df.iloc[0]["Sequence"],
                    "protein_length": int(df.iloc[0]["Length"]),
                    "matching_score": float(df.iloc[0]["Matching score"]),
                    "duration": spend_time
                    }
        except Exception as e:
            return {"error": str(e)}
            
if __name__ == '__main__':
    # Test
    tool = ProTrekText2Protein()
    
    input_args = {
        "protein_text": "Proteins with zinc bindings",
        "database": "Swiss-Prot",
    }

    for obs in tool.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # pinal.terminate()
    