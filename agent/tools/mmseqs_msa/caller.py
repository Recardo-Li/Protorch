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
class MmseqsMsa(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/mmseqs_msa", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, query_sequence, msa_mode) -> dict:
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        save_dir = f"{self.out_dir}/mmseqs_msa/{now}"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        if query_sequence is None:
            print("Required parameters:")
            print("  -i: The protein sequence used as the query for homology searches.")
        
        fasta_path = f"{save_dir}/examples.fasta"
        # save the sequence to fasta file
        self.sequence_to_fasta(fasta_path, query_sequence)
        save_path = f"{save_dir}/protein.a3m"
        
        # Call the mmseqs2 server
        cmd = f"bash {BASE_DIR}/command.sh input='{fasta_path}' output_dir='{save_dir}' msa_mode={msa_mode} > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)
            
            if os.path.exists(save_path):
                with open(save_path) as r:
                    contents = r.readlines()
                    results = [1 if content.startswith(">") else 0 for content in contents]
                    results_num = sum(results)
                spend_time = (datetime.datetime.now() - start).total_seconds()
                result = {"alignment_file": save_path[len(self.out_dir)+1:], "results_num": results_num, "duration": spend_time}
                if results_num == 1:
                    result["warning"] = "No homologous sequences found, only the query sequence is present."
                return result
            else:
                return {"alignment_file": "MMseqs2 encountered an error. Please check your inputs and options."}
        except Exception as e:
            return {"alignment_file": str(e)}

    def sequence_to_fasta(self, file_path, sequence):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(file_path, "w") as fasta_file:
            fasta_file.write(">protein\n")
            fasta_file.write(f"{sequence}\n")

if __name__ == '__main__':
    # Test
    mmseqs2 = MmseqsMsa(BASE_DIR)
    
    input_args = {
        "query_sequence": "AAAA",
        "msa_mode": "mmseqs2_uniref",
    }
    for obs in mmseqs2.mp_run(**input_args):
        os.system("clear")
        print(obs)
