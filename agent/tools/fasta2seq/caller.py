# Your main tool file (e.g., fasta2seq_tool.py)

import json
import sys
import os

# --- Assuming your project structure setup is correct ---
# This part is kept from your original code.
ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool
# ---------------------------------------------------------


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@register_tool
class Fasta2Seq(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/fasta2seq", **kwargs):
        super().__init__(
            # Assuming your config.yaml points to the improved return value format
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, fasta_file: str) -> dict:
        """
        Executes the FASTA parsing subprocess and returns the structured result.

        Args:
            fasta_file (str): Path to the input FASTA file.
                              Note: The original code forces this into self.out_dir.
                              A more typical design would be to accept an absolute/relative path directly.
                              We will keep the original behavior for this refactoring.

        Returns:
            dict: A dictionary containing the list of sequence records or an error message.
        """
        # Note: This path construction assumes the input file is located relative to the tool's output directory.
        # This might be specific to your framework's design.
        full_fasta_path = os.path.join(self.out_dir, fasta_file)
        
        cmd_args = {
            "fasta_file": full_fasta_path,
        }
        
        # Build the command to execute the worker script
        cmd = f"{self.config.get('python', sys.executable)} {os.path.join(BASE_DIR, 'command.py')}"
        for k, v in cmd_args.items():
            cmd += f" --{k} {v}"
        
        # Redirect the stdout (our JSON) and stderr (any errors) to the log file
        cmd += f" > {self.log_path} 2>&1"
        
        try:
            # Execute the command
            # print(f"Executing command: {cmd}") # Uncomment for debugging
            os.system(cmd)
            
            # Read the entire output from the log file
            with open(self.log_path, "r") as f:
                content = f.read()

            # Check if the subprocess produced any output
            if not content.strip():
                # This can happen if os.system fails or the script exits without printing
                raise ValueError("Log file is empty. The subprocess may have failed. Check log for errors.")

            # Parse the JSON content from the log file. This is much more robust.
            result = json.loads(content)
            
            result = result.get("sequence_records", [])
            
            if not result:
                return {"error": "No sequence records found in the FASTA file."}
            
            else:
                result = {"protein_sequence": result[0].get("sequence", "")}
            
            # The result from command.py is already in the final desired format.
            return result
                
        except json.JSONDecodeError:
            # This error is critical: it means the subprocess output was not valid JSON.
            error_msg = f"Error: Failed to decode JSON from subprocess output. See log for details: {self.log_path}"
            print(error_msg)
            return {"error": error_msg}
        except Exception as e:
            # Catch any other exceptions during the process
            print(f"An unexpected error occurred: {e}")
            return {"error": str(e)}


if __name__ == '__main__':
    # Instantiate the tool, pointing its output dir to our test directory
    # The tool will look for the input file inside this directory
    caller = Fasta2Seq(out_dir=BASE_DIR)
    
    # The input path is relative to the `out_dir` specified above
    input_args = {
        "fasta_file": "example/human_FP.fasta" 
    }

    for obs in caller.mp_run(**input_args):
        os.system("clear")
        print(obs)

