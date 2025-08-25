import sys

# Assuming the project structure is consistent with your example
ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch
import re

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool


torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class HMMScan(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/hmmscan", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "hmmscan"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.config["example_output"] = self.config["example_output"][tool_name]
        self.tool_name = tool_name
    
    def __call__(self, query_seq_file: str, hmm_database: str = 'Pfam-A', e_value_cutoff: float = 10.0, bit_score_cutoff: float = None, cpu: int = 1) -> dict:
        """
        Executes the hmmscan tool to search a sequence against an HMM database.

        Args:
            query_seq_file (str): Path to the input query sequence file (e.g., FASTA format).
            hmm_database (str): Name of the HMM database to use. Defaults to 'Pfam-A'.
            e_value_cutoff (float): E-value cutoff for reporting domains. Default is 10.0.
            bit_score_cutoff (float): Bit score cutoff for reporting domains. Default is None.
            cpu (int): Number of CPU threads to use. Default is 1.

        Returns:
            dict: A dictionary containing paths to the output files and other metrics.
        """
        # --- Input Validation ---
        query_path = os.path.join(self.out_dir, query_seq_file) if not os.path.isabs(query_seq_file) else query_seq_file

        if not os.path.exists(query_path):
            return {"error": f"Query file not found at path: {query_seq_file}"}

        db_path = self._get_database_path(hmm_database)

        start_time = datetime.datetime.now()

        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        save_dir = f"{self.out_dir}/{self.tool_name}/{timestamp}"
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # --- Define output paths based on YAML return values ---
        tblout_save_path = f"{save_dir}/results.tblout"
        domtblout_save_path = f"{save_dir}/results.domtblout"
        fasta_save_path = f"{save_dir}/hit_domains.fasta"

        # --- Command Construction ---
        # --tblout: per-sequence tabular output
        # --domtblout: per-domain tabular output
        # -E: E-value cutoff
        # -T: Bit score cutoff
        # --cpu: number of threads
        cmd_parts = [
            self.config.HMMscan,  # Path to the hmmscan executable
            f"--cpu {cpu}",
            f"-E {e_value_cutoff}",
            f"--tblout '{tblout_save_path}'",
            f"--domtblout '{domtblout_save_path}'",
            f"-o '{self.log_path}'",  # Directly log to file
        ]
        
        # Add bit score cutoff only if provided by the user
        if bit_score_cutoff is not None:
            cmd_parts.append(f"-T {bit_score_cutoff}")

        # Add positional arguments: <hmmdb> <seqfile>
        cmd_parts.append(f"'{db_path}'")
        cmd_parts.append(f"'{query_path}'")
        
        
        cmd = " ".join(cmd_parts)
        
        try:
            print(cmd)
            os.system(cmd)
    
            # The most informative output is domtblout, check its existence and size
            if os.path.exists(domtblout_save_path) and os.path.getsize(domtblout_save_path) > 0:
                duration = (datetime.datetime.now() - start_time).total_seconds()

                # Parse scores from the output
                scores = self._parse_domtblout(query_path, domtblout_save_path, fasta_save_path)
                
                # Prepare the final result dictionary according to the YAML documentation
                result = {
                    "tblout_file": tblout_save_path.replace(f"{self.out_dir}/", "", 1),
                    "domtblout_file": domtblout_save_path.replace(f"{self.out_dir}/", "", 1),
                    "hit_domains_fasta": fasta_save_path.replace(f"{self.out_dir}/", "", 1),
                    "duration": duration
                }
                result.update(scores)

                return result
            else:
                return {"error": f"HMMScan failed."}
        
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}

    def _parse_domtblout(self, query_fasta_path: str, domtblout_path: str, output_fasta_path: str):
        """
        Extracts domain sequences from the query FASTA based on domtblout coordinates.

        Args:
            query_fasta_path (str): Path to the input query sequence file.
            domtblout_path (str): Path to the hmmscan domtblout output file.
            output_fasta_path (str): Path to write the output FASTA file of extracted domains.
        """
        # Step 1: Read query sequences into a dictionary for quick lookup.
        # This parser is robust for standard FASTA files.
        sequences = {}
        try:
            with open(query_fasta_path, 'r') as f:
                header = None
                current_sequence = []
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('>'):
                        if header:
                            # Before starting a new sequence, save the previous one.
                            sequences[header] = ''.join(current_sequence)
                        # The identifier is the string after '>' and before the first whitespace.
                        # This is how hmmscan identifies sequences.
                        header = line[1:].split(maxsplit=1)[0]
                        current_sequence = []
                    else:
                        current_sequence.append(line)
                # Save the last sequence in the file
                if header:
                    sequences[header] = ''.join(current_sequence)
        except IOError as e:
            print(f"Error: Could not read query FASTA file '{query_fasta_path}'. {e}")
            return

        # For debugging: Check if sequences were loaded correctly.
        # print(f"Loaded {len(sequences)} sequences from FASTA file.")
        # print(f"Sequence IDs: {list(sequences.keys())[:5]}")

        # Step 2: Parse domtblout and write extracted domains to the output file.
        try:
            with open(domtblout_path, 'r') as fin, open(output_fasta_path, 'w') as fout:
                num_hit = 0
                accessions = []
                
                for line in fin:
                    if line.startswith('#'):
                        continue
                    
                    parts = re.split(r'\s+', line.strip())
                    
                    # A valid domtblout line has 22 fields. Check for this to avoid IndexErrors.
                    if len(parts) < 22:
                        continue

                    # --- CORRECT Column Mapping for hmmscan domtblout ---
                    # In hmmscan, the SEQUENCE is the "query" and the HMM is the "target".
                    
                    # (1) target name: The name of the HMM that matched.
                    hmm_name         = parts[0]
                    # (2) target accession: The accession of the HMM.
                    hmm_accession    = parts[1].split('.')[0] # Remove version for cleaner ID
                    # (4) query name: The name of your input sequence.
                    sequence_name    = parts[3]
                    # (13) i-Evalue: The independent E-value for this domain hit.
                    domain_i_evalue  = float(parts[12])
                    # (14) score: The bit score for this domain hit.
                    domain_score     = float(parts[13])
                    # (20) from (env coord on query): The envelope start on your sequence (1-based).
                    env_from         = int(parts[19])
                    # (21) to (env coord on query): The envelope end on your sequence (1-based).
                    env_to           = int(parts[20])

                    num_hit += 1
                    accessions.append(hmm_accession)

                    # For debugging: check the names being parsed from domtblout
                    # print(f"Checking for target '{target_name}' in sequence dictionary...")

                    if sequence_name in sequences:
                        full_sequence = sequences[sequence_name]
                        
                        # HMMER coordinates are 1-based and inclusive.
                        # Python slicing is 0-based and exclusive of the end index.
                        # So, [start-1:end] correctly extracts the substring.
                        domain_sequence = full_sequence[env_from - 1:env_to]
                        
                        if not domain_sequence:
                            # This can happen if coordinates are invalid, e.g., env_to < env_from
                            print(f"Warning: Extracted empty domain for {sequence_name} at {env_from}-{env_to}. Skipping.")
                            continue

                        # Create a descriptive FASTA header for the extracted domain
                        new_header = (f">{sequence_name}_{env_from}-{env_to} "
                                    f"hmm_name={hmm_name} "
                                    f"hmm_accession={hmm_accession} "
                                    f"e_value={domain_i_evalue:.2e} "
                                    f"score={domain_score}")
                        
                        fout.write(new_header + '\n')
                        # Write sequence with a fixed line width (e.g., 60 chars) for readability
                        for i in range(0, len(domain_sequence), 60):
                            fout.write(domain_sequence[i:i+60] + '\n')
                    # else:
                        # Uncomment this block for deep debugging to see exactly which IDs are not matching.
                        # print(f"Warning: Target name '{target_name}' from domtblout not found in FASTA keys.")

            most_frequent_accessions = sorted(set(accessions), key=accessions.count, reverse=True)
        
        except (IOError, ValueError) as e:
            print(f"Error: Could not process domtblout for domain extraction. Error: {e}")
        except IndexError as e:
            print(f"Error: An IndexError occurred, likely due to a malformed line in the domtblout file. Error: {e}. Line: '{line.strip()}'")
        if num_hit == 0:
            return {"error": "No hit in this scanning"}
        return {
            "top_accession": most_frequent_accessions[0],
            "total_hits": num_hit,
            "num_unique_accessions": len(set(accessions)),
        }

    def _get_database_path(self, database: str) -> str:
        """
        Constructs the full path to the pre-configured HMM database.
        """
        if database == "Pfam-A":
            # Assuming the path is stored in the main config file under a key like 'PFAM_DB'
            db_path = os.path.join(ROOT_DIR, self.config["PFAM_DB"])
            # HMMER requires the database to be pressed (binary indexed files)
            # The path should point to the main .hmm file.
            if not os.path.exists(db_path):
                 raise FileNotFoundError(f"Pfam-A database not found at configured path: {db_path}")
            return db_path
        else:
            raise ValueError(f"Unsupported HMM database: {database}. Only 'Pfam-A' is configured.")

if __name__ == '__main__':
    hmmscan = HMMScan(BASE_DIR)
    
    input_args = {
        "query_seq_file": "example/protein_sequence.fasta",
    }
    
    for obs in hmmscan.mp_run(**input_args):
        os.system("clear")
        print(obs)