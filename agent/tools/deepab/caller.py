import re
import shlex
import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch
import json

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class Deepab(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/deepab",**kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, heavy_chain_sequence, light_chain_sequence, decoys=5, renumber=True) -> dict:
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M")

        pred_dir = f"{self.out_dir}/deepab/{now}"
        os.makedirs(pred_dir, exist_ok=True)
        
        fasta_file =f"{pred_dir}/input.fasta"
        self.seq2fasta(fasta_file, heavy_chain_sequence, light_chain_sequence)
        model_dir = f'{ROOT_DIR}/{self.config["model_dir"]}'
        single_chain = False if heavy_chain_sequence and light_chain_sequence else True
        
        with open(self.log_path, 'a') as f:
            f.write("ready to enter deepab_main\n")
        
        cmd = f"{self.config['python']} {BASE_DIR}/command.py \
                                        --fasta_file {shlex.quote(fasta_file)} \
                                        --pred_dir {shlex.quote(pred_dir)} \
                                        --decoys {decoys} \
                                        --renumber {renumber} \
                                        --single_chain {single_chain} \
                                        --model_dir {shlex.quote(model_dir)} \
                                        > {self.log_path} 2>&1"
        try:
            os.system(cmd)  
        
            pdb_path = os.path.join(pred_dir, "pred.deepab.pdb")
            if os.path.exists(pdb_path):
                with open(f"{pred_dir}/metrics.json", "r") as r:
                    metrics = json.load(r)
                    rosetta_energy = metrics["min_score"]   
                print(f"Deepab successfully completed. Output saved to {pred_dir[len(self.out_dir)+1:]}.")
                return {"antibody_structure": pdb_path[len(self.out_dir)+1:], "rosetta_energy": rosetta_energy}
            
            else:
                return {"error": "Deepab encountered an error. Please check your inputs and options."}
        
        except Exception as e:
            return {"error": str(e)}

    def seq2fasta(self, file_path, heavy=None, light=None):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        with open(file_path, "w+") as fasta_file:
            fasta_file.write(">:H\n")
            # Remove spaces and newlines from the sequences
            heavy = re.sub(r'\s+', '', heavy) if heavy else ''
            light = re.sub(r'\s+', '', light) if light else ''
            fasta_file.write(f"{heavy}\n")

            fasta_file.write(">:L\n")
            fasta_file.write(f"{light}\n")

if __name__ == '__main__':
    # Test
    deepab = Deepab(BASE_DIR)
    
    input_args = {
        "heavy_chain_sequence": "EIQLQQSGPELVKPGASVKIS CKASGYSFTDYIMLWVKQSHGKSLEWIGNINPYYGSTSYNLKFKGKATLTVDKSSSTAYMQLNSLTSEDSAVYYCARKNYYGSSLDYWGQGTTLTVS",
        "light_chain_sequence": "DVVMTQTPFSLPVSLGDQASISCRSSQSLVHSNGNTYLHWYLQKPGQSPKLLIYKVSNRFSGVPDRFSGSGSGTDFTLKISRVEAEDLGVYFCSQSTHVPYTFGGGTKLEIK",
        "decoys": 5,
        "renumber": True
    }

    for obs in deepab.mp_run(**input_args):
        os.system("clear")
        print(obs)
    