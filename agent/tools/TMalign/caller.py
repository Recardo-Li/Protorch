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
class TMalign(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/TMalign", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, structure_path_1: str, structure_path_2: str) -> dict:
        """
        Compare two PDB files using TMalign
        Args:
            structure_path_1: Path to the first PDB file
            structure_path_2: Path to the second PDB file

        Returns:
            tmscore: TM-score
        """
        start_time = datetime.datetime.now()
        
        structure_path_1 = os.path.join(self.out_dir, structure_path_1)
        structure_path_2 = os.path.join(self.out_dir, structure_path_2)
        
        cmd = f"{ROOT_DIR}/{self.config.TMalign} {structure_path_1} {structure_path_2} > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)
            
            # Read the log file to get the result
            with open(self.log_path, "r") as r:
                tmscores = []
                for line in r:
                    if line.strip().startswith("TM-score"):
                        score = float(line.split("=")[1].strip().split(' ')[0])
                        tmscores.append(score)
                
                # Get the larger value as the final score
                tmscore = max(tmscores)
            spend_time = (datetime.datetime.now() - start_time).total_seconds()
            return {"tmscore": tmscore, "duration": spend_time}
        
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    tmalign = TMalign(f"{ROOT_DIR}/agent/tools/TMalign")
    
    input_args = {
        "structure_path_1": "example/2h35.pdb",
        "structure_path_2": "example/5hu6.pdb",
    }
    obs = tmalign.run(**input_args)
    print(obs)

    # for _ in range(2):
    #     for obs in tmalign.mp_run(**input_args):
    #         os.system("clear")
    #         print(obs)