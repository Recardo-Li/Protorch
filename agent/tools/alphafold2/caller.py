import sys
import time

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch
import json
import subprocess

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool


torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class Alphafold2(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/alphafold2", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, protein_sequence, msa_mode="mmseqs2_uniref_env"):
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M")

        result_dir = f"{self.out_dir}/alphafold2/{now}"
        os.makedirs(result_dir, exist_ok=True)

        tmp_path = result_dir
        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)
            
        # create tmp file, converting protein sequence into fasta file, as the input of alphafold
        fasta_file = os.path.join(tmp_path, "alphafold", f"alphafold_{now}.fasta")
        self.sequence_to_fasta(fasta_file, protein_sequence)


        cmd = f"bash {BASE_DIR}/cmd.sh input={fasta_file}\
                                                    output_dir={result_dir}\
                                                    msa_mode={msa_mode}"


        cmd += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)
            pdb_path = None
            for file in os.listdir(result_dir):
                if file.endswith(".pdb") and "rank_001" in file:
                    pdb_path = os.path.join(result_dir, file)
                    break
                
            # get return scores
            metric_path = None
            # init return scores
            avg_plddt = None
            max_pae = None
            ptm = None
            
            for file in os.listdir(result_dir):
                if file.endswith(".json") and "rank_001" in file:
                    metric_path = os.path.join(result_dir, file)
                    break
                
            if metric_path:
                with open(metric_path, 'r', encoding='utf-8') as file:
                    metric_dict = json.load(file) 
                    avg_plddt = sum(metric_dict["plddt"])/len(metric_dict["plddt"])
                    max_pae = metric_dict["max_pae"]
                    ptm = metric_dict["ptm"]

            if os.path.exists(pdb_path):
                return {"save_path": pdb_path[len(self.out_dir)+1:],
                        "avg_plddt": avg_plddt, "max_pae": max_pae, "ptm": ptm}
            else:
                return {"error": "PDB result of Alphafold2 not found."}
        
        except Exception as e:
            return {"error": str(e)}
        
    def sequence_to_fasta(self, file_path, sequence):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # check if it is multimer
        is_multimer = ":" in sequence

        with open(file_path, "w") as fasta_file:
            if is_multimer:
                # if true, use ":" to seperate sequences in fasta also
                fasta_file.write(">multimer\n")
                chains = sequence.split(":")
                for i, chain in enumerate(chains):
                    if i < len(chains) - 1:
                        fasta_file.write(f"{chain}:\n")
                    else:
                        fasta_file.write(f"{chain}\n")
            else:
                fasta_file.write(">protein\n")
                fasta_file.write(f"{sequence}\n")


if __name__ == '__main__':
    # Test
    alphafold2 = Alphafold2()
    
    input_args = {
        "protein_sequence": "MPEEEPVYIVKNKPVRLKCRASPAEQIYFKCNGEKVNQEKHTESEVVDPETGKKVREVEINVTRKQVEDFFGPEDYWCQCVAWSSAGPTRSDPARVQVAYLRDDFRQHPSSQDVVAGEPAVLECKPPRGIPEAEISWLKDGEPIDPEKDPNYQILPNGNLLISSATLSDSANYQCVAKNIAAKRRSHVAKVYVYEKSSL",
    }
    
    for obs in alphafold2.mp_run(**input_args):
        os.system("clear")
        print(obs)

        # alphafold2.terminate()
    