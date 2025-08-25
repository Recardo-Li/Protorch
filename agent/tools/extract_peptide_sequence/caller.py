import sys
import os
import json

BASE_DIR = os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

@register_tool
class ExtractPeptideSequenceTool(BaseTool):
    def __init(self, out_dir: str = os.path.join(os.getcwd(), 'output', 'extract_peptide_sequence'), **kwargs):
        super().__init__(
            config_path=os.path.join(BASE_DIR, 'config.yaml'),
            out_dir=out_dir,
            **kwargs
        )

        def __call__(self, protein_sequence: str, start: int, end: int)->dict:
            #Validate indices
            if start < 1 or end > len(protein_sequence) or start >= end:
                return {"error": "Invalid start or end residue index."}
            
            # Extract peptide sequence
            cmd_args = {
                "protein_sequence": protein_sequence,
                "start": start,
                "end": end  
            }
            python_exec = self.config.get('python', sys.executable)
            cmd = f"{python_exec} {os.path.join(BASE_DIR, 'command.py')}"
            for k, v in cmd_args.items():
                cmd += f" --{k} '{v}'"
            
            cmd += f" > {self.log_path} 2>&1"

            os.system(cmd)

            # Read log file content
            try:
                with open(self.log_path, 'r') as f:
                    lines = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                return {"error": "Log file not found."}
            
            if not lines:
                return {"error": "Empty log file. Subprocess may have failed."}
            
            # Parse the last JSON as result
            try:
                results = json.loads(lines[-1])
            except json.JSONDecodeError:
                return {"error": "Failed to parse JSON result from log."}
            
            return results

if __name__ == "__main__":
    tool = ExtractPeptideSequenceTool()
    args = {
        "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQDILDLIYQY",
        "start": 1,
        "end": 10
    }
    for obs in tool.mp_run(**args):
        print(obs)