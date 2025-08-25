import sys
import os
import datetime
import re # Import regular expressions for robust parsing

# --- Assuming ROOT_DIR is correctly set by your framework ---
# For standalone testing, we can define it here.
try:
    ROOT_DIR = __file__.rsplit("/", 4)[0]
except IndexError:
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
# ----------------------------------------------------------------

# Assuming these are part of your framework
from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@register_tool
class HHAlignMSA(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/hhalign_msa", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "hhalign_msa"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.config["example_output"] = self.config["example_output"][tool_name]
        self.tool_name = tool_name
    
    def __call__(self, query_msa: str, template_msa: str, mact: float = 0.1, output_path: str = None) -> dict:
        """
        Executes the hhalign tool with the given query and template.

        Args:
            query (str): The path to the query input file (A3M or HMM).
            template (str): The path to the template input file (A3M or HMM).
            mact (float): MAC (Maximum Accuracy) alignment threshold. Default is 0.1.
            output_path (str, optional): Specific path to save the result file. Defaults to None.

        Returns:
            dict: A dictionary containing the path to the result and parsed scores.
        """
        # NOTE: The original code assumed inputs are relative to self.out_dir.
        # This can be risky. It's often better to expect full paths or resolve them carefully.
        # I'm keeping the original logic but adding a print for clarity.
        # For a robust tool, consider using os.path.abspath(query)
        query_path = os.path.join(self.out_dir, query_msa) if not os.path.isabs(query_msa) else query_msa
        template_path = os.path.join(self.out_dir, template_msa) if not os.path.isabs(template_msa) else template_msa


        if not os.path.exists(query_path) or not os.path.exists(template_path):
            return {"error": f"Input file not found. Checked paths: {query_msa}, {template_msa}"}

        start_time = datetime.datetime.now()
        
        if output_path:
            # Use user-provided output path
            save_path = os.path.join(self.out_dir, output_path) if not os.path.isabs(output_path) else output_path
            save_dir = os.path.dirname(save_path)
        else:
            # Generate a unique output path
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            save_dir = f"{self.out_dir}/hhalign_msa/{timestamp}"
            save_path = f"{save_dir}/hhalign_result.hhr"
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # --- Corrected command construction ---
        # -i: query input
        # -t: template input
        # -o: output HHR file
        # -mact: alignment sensitivity parameter
        # We redirect only stderr (2>) to the log, as stdout is captured by the -o flag.
        cmd = (f"{self.config.HHalign} -i '{query_path}' -t '{template_path}' "
               f"-o '{save_path}' -mact {mact} > /dev/null 2> {self.log_path}")
        


        try:
            os.system(cmd) 
    
            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                duration = (datetime.datetime.now() - start_time).total_seconds()
                
                # Parse the rich output from the .hhr file
                scores = self._parse_hhr_output(save_path)
                
                # Prepare the final result dictionary
                result = {
                    "report": save_path.replace(f"{self.out_dir}/", "", 1),
                    "duration": duration
                }
                result.update(scores) # Merge the parsed scores
                
                return result
            else:
                with open(self.log_path, 'r') as log_file:
                    error_message = log_file.read()
                return {"error": f"HHalign failed. Log content: {error_message}"}
        
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}
    
    def _parse_hhr_output(self, hhr_path: str) -> dict:
        """
        Parses the .hhr output file to extract key alignment scores.
        """
        scores = {
            "prob": None,
            "evalue": None,
            "score": None,
            "aligned_cols": None,
            "identities": None,
            "similarity": None,
        }
        try:
            with open(hhr_path, "r") as f:
                for line in f:
                    # The main scores are on a line starting with "Probab"
                    if line.startswith("Probab"):
                        # Example line: Probab=99.52  E-value=2.1e-25  Score=150.23  Aligned_cols=105  Identities=35%  Similarity=0.452  Sum_probs=...
                        parts = line.split()
                        for part in parts:
                            if "=" in part:
                                key, value = part.split('=', 1)
                                if key == "Probab":
                                    scores["prob"] = float(value)
                                elif key == "E-value":
                                    scores["evalue"] = float(value)
                                elif key == "Score":
                                    scores["score"] = float(value)
                                elif key == "Aligned_cols":
                                    scores["aligned_cols"] = int(value)
                                elif key == "Identities":
                                    scores["identities"] = float(value.replace('%', ''))
                                elif key == "Similarity":
                                    scores["similarity"] = float(value)
                        break # Found the line, no need to read further
        except (IOError, ValueError, IndexError) as e:
            print(f"Warning: Could not parse HHR file '{hhr_path}'. Error: {e}")
        
        return scores


if __name__ == '__main__':
    # Test
    hhalign = HHAlignMSA(BASE_DIR)
    
    input_args = {
        "query_msa": f"example/example.a3m",
        "template_msa": f"example/protein_sequence.a3m"
    }
    
    for obs in hhalign.mp_run(**input_args):
        os.system("clear")
        print(obs)
    