import sys
import time
import biotite.structure.io as bsio

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool


BASE_DIR = os.path.dirname(__file__)


@register_tool
class Esmfold(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/esmfold", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, protein_sequence) -> dict:
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M")
        save_path = f"{self.out_dir}/esmfold/{now}/esmfold_prediction.pdb"
        
        cmd_args = {
            "sequence": protein_sequence,
            "save_path": save_path,
            "model_path": f"{ROOT_DIR}/{self.config['model_path']}",
            "device": "cuda:1",
        }
        
        # Call the ESMFold model
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            cmd += f" --{k} {v}"
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        try:
            os.system(cmd)  
        
            if os.path.exists(save_path):
                struct = bsio.load_structure(save_path, extra_fields=["b_factor"])
                avg_plddt = float(struct.b_factor.mean())
                return {"save_path": save_path[len(self.out_dir)+1:], "avg_plddt": avg_plddt}
            
            else:
                return {"error": "Failed to run esmfold"}
        
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    esmfold = Esmfold()
    
    input_args = {
        "protein_sequence": "AAAAAAA",
    }

    for obs in esmfold.mp_run(**input_args):
        os.system("clear")
        print(obs)
