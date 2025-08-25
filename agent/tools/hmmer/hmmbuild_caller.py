import sys

# Assume this setup is in your main script or a shared module
# This ensures the project's root is in the Python path
ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import os
import datetime
from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(__file__)


@register_tool
class HMMBuild(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/hmmbuild", **kwargs):
        """
        Initializes the HMMBuild tool wrapper.
        """
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "hmmbuild"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.config["example_output"] = self.config["example_output"][tool_name]
        self.tool_name = tool_name

    def __call__(self, msa_file: str, hmm_name: str = None, cpu: int = 1) -> dict:
        """
        Executes the hmmbuild tool to create a profile HMM from a Multiple Sequence Alignment (MSA).
        It automatically handles the conversion of A3M files from hhblits.

        Args:
            msa_file_path (str): Path to the input MSA file (e.g., from hhblits in A3M format, or a standard FASTA alignment).
            hmm_name (str, optional): The name to assign to the HMM. If None, it's derived from the input file name.
            cpu (int): Number of CPU threads to use. Default is 1.

        Returns:
            dict: A dictionary containing the path to the generated HMM profile file and other metrics.
        """
        # --- Input Validation ---
        msa_abs_path = os.path.join(self.out_dir, msa_file) if not os.path.isabs(msa_file) else msa_file
        
        if not os.path.exists(msa_abs_path):
            return {"error": f"Input MSA file not found at path: {msa_file}"}
        
        start_time = datetime.datetime.now()
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        
        msa_basename = os.path.basename(msa_file).split('.')[0]
        save_dir = f"{self.out_dir}/hmmbuild/{timestamp}"
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # --- Set up command arguments ---
        if hmm_name is None:
            hmm_name = msa_basename
        
        hmm_name = hmm_name.replace(" ", "_")  # Replace spaces with underscores for file naming
        
        hmm_output_path = os.path.join(save_dir, f"{hmm_name}.hmm")
        
        # Command construction for hmmbuild
        # --cpu: number of threads
        # --name: assign a name to the HMM
        # The two main arguments are the output HMM file and the input MSA file.
        cmd = (f"{self.config.HMMbuild} --cpu {cpu} -n '{hmm_name}' "
               f"'{hmm_output_path}' '{msa_abs_path}' "
               f"> {self.log_path} 2>&1")

        try:
            os.system(cmd)

            if os.path.exists(hmm_output_path) and os.path.getsize(hmm_output_path) > 0:
                duration = (datetime.datetime.now() - start_time).total_seconds()
                
                scores = self._parse_hmmbuild_stdout(self.log_path)
                
                result = {
                    "hmm_profile_file": hmm_output_path.replace(f"{self.out_dir}/", "", 1),
                    "duration": duration,
                    "hmm_name": hmm_name
                }
                
                result.update(scores)
                return result
            else:
                with open(self.log_path, 'r') as log_file:
                    error_message = log_file.read()
                return {"error": f"hmmbuild failed. Log content: {error_message}"}

        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}

    def _parse_hmmbuild_stdout(self, stdout_path: str) -> dict:
        """
        Parses the standard output of hmmbuild to extract key statistics about the generated HMM.
        """
        stats = {
            "num_sequences": None,
            "alignment_length": None,
            "model_length": None,
            "effective_num_sequences": None,
            "relative_entropy_per_pos": None,
        }
        try:
            with open(stdout_path, "r") as f:
                lines = f.readlines()

            # Find the summary table line. It's the one after the header.
            header_found = False
            for line in lines:
                if line.strip().startswith("#----"):
                    header_found = True
                    continue
                
                if header_found and line.strip() and not line.strip().startswith("#"):
                    parts = line.split()
                    # Example line: 1 MyTestProteinHMM 3 42 41 2.00 0.952 -
                    if len(parts) >= 7:
                        stats["num_sequences"] = int(parts[2])
                        stats["alignment_length"] = int(parts[3])
                        stats["model_length"] = int(parts[4])
                        stats["effective_num_sequences"] = float(parts[5])
                        stats["relative_entropy_per_pos"] = float(parts[6])
                    break # We only need the first data line
        
        except (IOError, ValueError, IndexError) as e:
            print(f"Warning: Could not fully parse hmmbuild stdout file '{os.path.basename(stdout_path)}'. Error: {e}")

        return stats

if __name__ == '__main__':
    hmmbuild = HMMBuild(BASE_DIR)
    
    input_args = {
        "msa_file": "example/human_FP.aln",
        "hmm_name": "Human FP"
    }
    
    for obs in hmmbuild.mp_run(**input_args):
        os.system("clear")
        print(obs)
    

