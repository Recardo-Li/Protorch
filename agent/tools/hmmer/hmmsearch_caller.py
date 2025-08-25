import sys

# Assume this setup is in your main script or a shared module
# This ensures the project's root is in the Python path
try:
    ROOT_DIR = __file__.rsplit("/", 4)[0]
except IndexError:
    # Handle cases where the script is in the root directory
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import os
import datetime
import re
from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

# HMMSearch requires Biopython to parse FASTA files for domain extraction.
try:
    from Bio import SeqIO
except ImportError:
    print("Warning: Biopython is not installed. The 'hit_domains_fasta' output will not be generated.")
    print("Please install it with: pip install biopython")
    SeqIO = None

BASE_DIR = os.path.dirname(__file__)


@register_tool
class HMMSearch(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/hmmsearch", **kwargs):
        """
        Initializes the HMMSearch tool wrapper.
        """
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "hmmsearch"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.config["example_output"] = self.config["example_output"][tool_name]
        self.tool_name = tool_name

    def __call__(self, hmm_file: str, seq_db: str, e_value_cutoff: float = 10.0, bit_score_cutoff: float = None, cpu: int = 1) -> dict:
        """
        Executes the hmmsearch tool to find homologs of a profile HMM in a sequence database.

        Args:
            hmm_file (str): Path to the input profile HMM file.
            seq_db (str): Path to the target sequence database file (e.g., in FASTA format).
            e_value_cutoff (float): Report sequences with an E-value <= this value. Default is 10.0.
            bit_score_cutoff (float, optional): Report sequences with a bit score >= this value.
            cpu (int): Number of parallel CPU threads to use. Default is 1.

        Returns:
            dict: A dictionary containing paths to the output files and other metrics.
        """
        # --- Input Validation ---
        hmm_file_abs_path = os.path.join(self.out_dir, hmm_file) if not os.path.isabs(hmm_file) else hmm_file
        seq_db_abs_path = os.path.join(self.out_dir, seq_db) if not os.path.isabs(seq_db) else seq_db

        if not os.path.exists(hmm_file_abs_path):
            return {"error": f"Input HMM file not found at path: {hmm_file}"}
        if not os.path.exists(seq_db_abs_path):
            return {"error": f"Input sequence database not found at path: {seq_db}"}

        start_time = datetime.datetime.now()
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        
        save_dir = f"{self.out_dir}/hmmsearch/{timestamp}"
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # --- Set up output file paths ---
        stdout_path = os.path.join(save_dir, "hmmsearch.log")
        tblout_path = os.path.join(save_dir, "hits.tblout")
        domtblout_path = os.path.join(save_dir, "hits.domtblout")
        hit_domains_fasta_path = os.path.join(save_dir, "hit_domains.fasta")
        
        # --- Command Construction ---
        cmd_parts = [
            self.config.HMMsearch,
            f"--cpu {cpu}",
            f"-E {e_value_cutoff}",
            f"--tblout '{tblout_path}'",
            f"--domtblout '{domtblout_path}'",
            f"-o {self.log_path}"
        ]
        
        if bit_score_cutoff is not None:
            cmd_parts.append(f"-T {bit_score_cutoff}")
            
        cmd_parts.extend([
            f"'{hmm_file_abs_path}'",
            f"'{seq_db_abs_path}'"
        ])
        
        cmd = " ".join(cmd_parts)
        
        try:
            # --- Execute Command ---
            os.system(cmd)

            # --- Post-processing and Result Assembly ---
            if os.path.exists(domtblout_path) and os.path.getsize(domtblout_path) > 0:
                duration = (datetime.datetime.now() - start_time).total_seconds()
                
                # Extract hit domain sequences into a new FASTA file
                num_hits_found = self._extract_hit_domains(domtblout_path, seq_db_abs_path, hit_domains_fasta_path)

                
                result = {
                    "tblout_file": tblout_path.replace(f"{self.out_dir}/", "", 1),
                    "domtblout_file": domtblout_path.replace(f"{self.out_dir}/", "", 1),
                    "hit_domains_fasta": hit_domains_fasta_path.replace(f"{self.out_dir}/", "", 1),
                    "num_hits_found": num_hits_found,
                    "duration": duration,
                }
                
                return result
            else:
                return {"error": f"hmmsearch failed or found no hits."}

        except Exception as e:
            return {"error": f"An unexpected error occurred during hmmsearch execution: {str(e)}"}


    def _extract_hit_domains(self, domtblout_path: str, seq_db_path: str, output_fasta_path: str):
        """
        Parses a domtblout file and extracts the corresponding domain sequences
        from the sequence database into a new FASTA file.
        Requires Biopython.
        """
        print("Extracting hit domain sequences...")
        try:
            # 1. Read the sequence database into a dictionary for fast lookup
            seq_dict = SeqIO.to_dict(SeqIO.parse(seq_db_path, "fasta"))
            
            with open(output_fasta_path, "w") as out_f:
                with open(domtblout_path, "r") as in_f:
                    domain_counter = 0
                    for line in in_f:
                        if line.startswith("#"):
                            continue
                        
                        # 2. Parse the space-delimited domtblout line
                        parts = line.split()
                        target_name = parts[0]
                        # HMMER domain coordinates are 1-based
                        hmm_from = int(parts[17])
                        hmm_to = int(parts[18])
                        ali_from = int(parts[19])
                        ali_to = int(parts[20])
                        i_evalue = float(parts[12])
                        
                        # 3. Retrieve the full sequence
                        record = seq_dict.get(target_name)
                        if not record:
                            print(f"Warning: Sequence ID '{target_name}' from domtblout not found in '{os.path.basename(seq_db_path)}'. Skipping.")
                            continue
                        
                        domain_counter += 1
                        
                        # 4. Create a new, informative FASTA header
                        # Format: >original_id|domain_N|coords_start-end|evalue
                        new_header = f">{target_name}|domain_{domain_counter}|coords_{ali_from}-{ali_to}|evalue_{i_evalue}"
                        
                        # 5. Extract the subsequence (Python is 0-based, HMMER is 1-based)
                        # The coordinates ali_from and ali_to are inclusive.
                        subsequence = record.seq[ali_from - 1 : ali_to]
                        
                        # 6. Write to the output FASTA file
                        out_f.write(f"{new_header}\n")
                        out_f.write(f"{str(subsequence)}\n")
            print(f"Successfully wrote {domain_counter} domains to '{os.path.basename(output_fasta_path)}'.")

        except Exception as e:
            print(f"Error during domain extraction: {e}")
        return domain_counter

if __name__ == '__main__':
    hmmsearch = HMMSearch(BASE_DIR)
    
    input_args = {
        "hmm_file": "example/human_FP.hmm",
        "seq_db": "example/human_FP_full-length.fasta",
    }
    
    for obs in hmmsearch.mp_run(**input_args):
        os.system("clear")
        print(obs)
    