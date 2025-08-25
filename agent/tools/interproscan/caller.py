import sys

import pandas as pd
import os
from typing import List, Dict, Any

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
class InterproScan(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/interproscan", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, fasta_file, goterms=False, pathways=False) -> dict:
        fasta_file = f"{self.out_dir}/{fasta_file}"
        start_time = datetime.datetime.now()
        now = start_time.strftime("%Y%m%d_%H%M")
        save_dir = f"{self.out_dir}/interproscan/{now}"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        temp_dir = f"{save_dir}/temp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        seqs = self._read_fasta_to_list(fasta_file)
        seqtype = self._is_protein_sequence(seqs)
        
        # Call the InterproScan
        cmd = f"{BASE_DIR}/{self.config.script} \
                interproscan_cmd='{ROOT_DIR}/{self.config.InterproScan} -i {fasta_file} -d {save_dir}"
        
        cmd += f" -T {temp_dir}"
        if goterms:
            cmd += " -goterms"
        if pathways:
            cmd += " -pa"
        if seqtype:
            cmd += f" -t p'"
        else:
            cmd += f" -t n'"
        
        cmd += f">{self.log_path} 2>&1"
        try:
            os.system(cmd)  
            end_time = datetime.datetime.now()
            spend_time = (end_time - start_time).total_seconds()
            
            # clean up temp directory if it is empty
            if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                os.rmdir(temp_dir)
            
            if os.listdir(save_dir):
                origin_tsv = f"{save_dir}/{os.path.split(fasta_file)[-1]}.tsv"
                parsed_tsv = f"{save_dir}/{os.path.split(fasta_file)[-1]}.parsed.tsv"
                scores = self._parse_interproscan_tsv(origin_tsv, parsed_tsv)
                
                results = {"parsed_tsv": parsed_tsv[len(self.out_dir)+1:], "output_dir": save_dir[len(self.out_dir)+1:], "duration": spend_time}
                
                results.update(scores)
                
                return results
            
            else:
                raise Exception("InterproScan encountered an error. Please check your inputs and options.")
        
        except Exception as e:
            return {"error": str(e)}
        
    def _is_protein_sequence(self, sequences):
        sequence = "".join(sequences)
        # ATCG AUCG
        if len(set(sequence.upper())) > 6:
            return True
        else:
            return False
    
    def _read_fasta_to_list(self, file_path):
        sequences = []
        current_header = None
        current_seq = []
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    if current_header is not None: 
                        sequences.append("".join(current_seq))
                    current_header = line[1:]  
                    current_seq = []
                else:
                    current_seq.append(line)
            
            if current_header is not None:
                sequences.append("".join(current_seq))
        
        return sequences

    def _parse_interproscan_tsv(self, tsv_file: str, parsed_tsv_file: str) -> pd.DataFrame:
        """
        Parses the InterProScan TSV output file into a pandas DataFrame based on official documentation.

        This function is designed to be robust to the variable number of columns that
        InterProScan can output.

        Args:
            tsv_file (str): The path to the .tsv output file from InterProScan.

        Returns:
            pd.DataFrame: A DataFrame containing the annotation data. Returns an
                        empty DataFrame if the file is empty or an error occurs.
        """
        
        try:
            # Define the full set of possible column names in the correct order as per the documentation.
            all_possible_columns = [
                "Protein_Accession",
                "Sequence_MD5",
                "Sequence_Length",
                "Analysis",
                "Signature_Accession",
                "Signature_Description",
                "Start_Location",
                "Stop_Location",
                "Score",
                "Status",
                "Date",
                "InterPro_Accession",
                "InterPro_Description",
                "GO_Annotations",
                "Pathway_Annotations"
            ]

            # Read the file using pandas.
            # header=None: The file has no header row.
            # sep='\t': It's a tab-separated file.
            # na_values='-': Crucially, this tells pandas to interpret the hyphen character as a missing value (NaN).
            df = pd.read_csv(tsv_file, sep='\t', header=None, na_values='-')

            # Get the actual number of columns present in the file.
            num_cols = df.shape[1]

            # Assign the correct column names by slicing our master list.
            # This makes the function robust to whether optional columns are present or not.
            df.columns = all_possible_columns[:num_cols]

            # --- Data Type Conversion for better analysis ---
            # Convert location and length columns to nullable integers.
            # 'Int64' (capital 'I') allows for NaN values, which is essential.
            for col in ["Sequence_Length", "Start_Location", "Stop_Location"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

            # Convert score to numeric (float).
            if "Score" in df.columns:
                df["Score"] = pd.to_numeric(df["Score"], errors='coerce')
            
            # Convert Date to datetime objects
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors='coerce')

            df.to_csv(parsed_tsv_file, index=False, sep="\t")
            if len(df) == 0:
                return {
                    "top_accession": None,
                    "top_accession_name": None,
                    "total_hits": 0,
                    "num_unique_annotations": 0,
                    "error": "No hits found in the InterProScan results."
                }
            
            return {
                "top_accession": df["InterPro_Accession"].value_counts().idxmax() if "InterPro_Accession" in df.columns else None,
                "top_accession_name": df["InterPro_Description"].value_counts().idxmax() if "InterPro_Description" in df.columns else None,
                "total_hits": len(df),
                "num_unique_annotations": df["InterPro_Accession"].nunique() if "InterPro_Accession" in df.columns else 0,
            }

        except pd.errors.EmptyDataError:
            return {
                "top_accession": None,
                "top_accession_name": None,
                "total_hits": 0,
                "num_unique_annotations": 0,
                "error": "No hits found in the InterProScan results."
            }
        except Exception as e:
            return {
                "error": f"An error occurred while parsing the TSV file: {str(e)}",
                "top_accession": None,
                "top_accession_name": None,
                "total_hits": 0,
                "num_unique_annotations": 0,
                "error": "No hits found in the InterProScan results."
            }

if __name__ == '__main__':
    # Test
    interproscan = InterproScan(BASE_DIR)
    
    input_args = {
        "fasta_file": "example/example_1.fasta"
    }
    for obs in interproscan.mp_run(**input_args):
        os.system("clear")
        print(obs)
    