import ast
import sys
import time
ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import os
from agent. tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(__file__)

@register_tool
class PDB2Seq(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/pdb2seq", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )

    def __call__(self, pdb_file) -> dict:
        try:
            # Prepare the input file path
            pdb_file = os.path.join(self.out_dir, pdb_file)

            # Build command arguments
            cmd_args = {
                "pdb_file": pdb_file,
            }

            # Construct the command string
            cmd = f"{self.config['python']} {BASE_DIR}/command.py"
            for k, v in cmd_args.items():
                cmd += f" --{k} {v}"

            # Redirect output to log file
            cmd += f" > {self.log_path} 2>&1"

            # Execute the command and wait for completion
            os.system(cmd)

            # Parse the log file content
            sequence = None
            protein_length = None

            with open(self.log_path, "r") as f:
                lines = [line.strip() for line in f if line.strip()]
                
                for line in lines:
                    if line.startswith("Sequence:"):
                        if sequence is not None:
                            return {"error": "Multiple protein chains found in the PDB file. Please provide a PDB file with a single chain."}
                        sequence = line.split(":", 1)[1].strip()
                    elif line.startswith("Length:"):
                        if protein_length is not None:
                            return {"error": "Multiple protein chains found in the PDB file. Please provide a PDB file with a single chain."}
                        protein_length = int(line.split(":", 1)[1].strip())
                
                return {
                    "protein_sequence": sequence,
                    "protein_length": protein_length
                }
                
        except Exception as e:
            return {"error": str(e)}

# Example usage
if __name__ == "__main__":
    caller = PDB2Seq(BASE_DIR)
    input_args = {
        "pdb_file": "example/1A2B.pdb",
    }
    for obs in caller.mp_run(**input_args):
        os.system("clear")
        print(obs)