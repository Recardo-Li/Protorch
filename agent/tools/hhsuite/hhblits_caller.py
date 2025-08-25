import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool


torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class HHBlits(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/hhblits", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "hhblits"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.config["example_output"] = self.config["example_output"][tool_name]
        self.tool_name = tool_name
    
    def __call__(self, query: str, database: str = 'uniclust30', n_iter: int = 2, evalue: float = 0.001, cpu: int = 1) -> dict:
        """
        Executes the hhblits tool to search a database for homologous sequences.

        Args:
            query (str): Path to the input query file (e.g., FASTA format).
            database (str): Name of the database selected.
            n_iter (int): Number of search iterations. Default is 2.
            evalue (float): E-value cutoff for inclusion in the MSA. Default is 0.001.
            cpu (int): Number of CPU threads to use. Default is 1.
            output_path (str, optional): Specific path to save the result file. Defaults to None.

        Returns:
            dict: A dictionary containing the path to the alignment file and other metrics.
        """
        # --- Input Validation ---
        query_path = os.path.join(self.out_dir, query) if not os.path.isabs(query) else query

        if not os.path.exists(query_path):
            return {"error": f"Query file not found at path: {query}"}

        db_path_prefix = self._get_database_path(database)

        start_time = datetime.datetime.now()
        

        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        save_dir = f"{self.out_dir}/hhblits/{timestamp}"
        a3m_save_path = f"{save_dir}/{os.path.basename(query).split('.')[0]}.a3m"
        hhr_save_path = f"{save_dir}/{os.path.basename(query).split('.')[0]}_align-detail.hhr"
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # --- Corrected and Robust Command Construction ---
        # -i: query input file
        # -d: database
        # -oa3m: output MSA file in A3M format
        # -n: number of iterations
        # -e: e-value
        # -cpu: number of threads
        
        cmd = (f"{self.config.HHblits} -i '{query_path}' -d '{db_path_prefix}' "
               f"-oa3m '{a3m_save_path}' -o {hhr_save_path} -n {n_iter} -e {evalue} -cpu {cpu} "
               f"> /dev/null 2> {self.log_path}")
        
        try:
            os.system(cmd)
    
            if os.path.exists(a3m_save_path) and os.path.getsize(a3m_save_path) > 0:
                duration = (datetime.datetime.now() - start_time).total_seconds()
                
                scores = self._parse_hhr_output(hhr_save_path)
                # Prepare the final result dictionary according to the new documentation
                result = {
                    "msa_file": a3m_save_path.replace(f"{self.out_dir}/", "", 1),
                    "report": hhr_save_path.replace(f"{self.out_dir}/", "", 1),
                    "duration": duration
                }
                result.update(scores)

                return result
            else:
                with open(self.log_path, 'r') as log_file:
                    error_message = log_file.read()
                return {"error": f"HHblits failed. Log content: {error_message}"}
        
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}

    def _parse_hhr_output(self, hhr_path: str) -> dict:
        """
        Parses the .hhr output file to extract the top hit's ID and key scores,
        plus the total number of hits. This function is designed to be robust
        against empty or malformed files.
        """
        # This ensures it's always present in the return value, even if no hits are found.
        scores = {
            "msa_length": 0,
            "top_hit_id": None,
            "top_hit_probability": None,
            "top_hit_evalue": None,
            "top_hit_score": None,
        }
        try:
            with open(hhr_path, "r") as f:
                lines = f.readlines()

            # Find the start of the summary table to count hits
            summary_started = False
            hit_lines = []
            for line in lines:
                # The summary table starts after the "No Hit" header line
                if line.strip().startswith("No Hit"):
                    summary_started = True
                    continue
                if summary_started:
                    # The summary ends with a blank line or the start of alignments ('>')
                    if line.strip() == "" or line.startswith(">"):
                        break
                    hit_lines.append(line)
            
            scores["num_hits"] = len(hit_lines)

            # If hits were found, parse the top one from both the summary and detailed sections
            if scores["num_hits"] > 0:
                top_hit_summary = hit_lines[0].split()
            
                top_hit_id = top_hit_summary[1]
                scores["top_hit_id"] = top_hit_id

                # --- KEY CHANGE ENDS HERE ---

                # 1. Parse the summary line for Prob, E-value, and Score
                scores["top_hit_probability"] = float(top_hit_summary[2])
                scores["top_hit_evalue"] = float(top_hit_summary[3])
                scores["top_hit_score"] = float(top_hit_summary[4])

            else:
                scores["error"] = "No hits found in this search."
            
        except (IOError, ValueError, IndexError) as e:
            # This ensures the tool doesn't crash if parsing fails
            # The print statement is good for debugging.
            print(f"Warning: Could not fully parse HHR file '{os.path.basename(hhr_path)}'. Error: {e}")
        
        return scores

    def _get_database_path(self, database: str) -> str:
        """
        Constructs the full path to the database file based on the provided database name.
        This is useful for ensuring the correct path is used in commands.
        """
        if database == "uniclust30":
            return os.path.join(ROOT_DIR, self.config["UNICLUST"])
        else:
            raise ValueError(f"Unsupported database: {database}.")

if __name__ == '__main__':
    # Test
    hhblits = HHBlits(BASE_DIR)
    
    input_args = {
        "query": "example/protein_sequence.fasta",
        "n_iter": 2,
        "evalue": 1e-3,
    }
    for obs in hhblits.mp_run(**input_args):
        os.system("clear")
        print(obs)
