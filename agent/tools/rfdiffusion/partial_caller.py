import datetime
import os
import sys


ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import torch
import pickle

from agent.tools.rfdiffusion.runrf import RFExecutor
from agent.tools.register import register_tool
from agent.tools.base_tool import BaseTool


torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)


@register_tool
class RFPartialCaller(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/rfdiffusion_partial_diffusion", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "rfdiffusion_partial_diffusion"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.tool_name = tool_name
        
    def __call__(self, contigs, protein_structure, iterations=50, symmetry=None, order=1, hotspot=None,
                 chains=None, num_designs=1) -> dict:
        protein_structure = f"{self.out_dir}/{protein_structure}"
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M")
        rf_root = ROOT_DIR+'/'+self.config["rf_root"]
        out_dir = f"{self.out_dir}/rfdiffusion/{now}"
        try:
            executor = RFExecutor(rf_root, out_dir, self.config["python"], iterations, symmetry, order, hotspot,
                                chains, num_designs)
            ret = executor.run_diffusion(contigs, protein_structure, self.log_path)
            avg_plddts = self.get_avg_plddts(out_dir)
            # select the best sample
            avg_plddt = max(avg_plddts)
            max_index = avg_plddts.index(avg_plddt)
            if "design" in ret and "error" not in ret:
                return {"design": f"{out_dir[len(self.out_dir)+1:]}/design_{max_index}.pdb", "avg_plddt": avg_plddt}
            else:
                return ret
        
        except Exception as e:
            return {"error": str(e)}

    def get_avg_plddts(self, path):
        avg_plddts = []
        files = os.listdir(path)
        files = [file for file in files if file.endswith(".trb")]
        for file in files:
            with open(f"{path}/{file}", "rb") as f:
                metrics = pickle.load(f)
            last_step_plddts = metrics["plddt"][-1]
            avg_plddt = sum(last_step_plddts)/len(last_step_plddts)*100
            avg_plddts.append(float(avg_plddt))
        return avg_plddts
    
if __name__ == "__main__":
    caller = RFPartialCaller()
    
    input_args = {
        "contigs": "A1-10",
        "protein_structure": "5TPN.pdb"
    }

    for obs in caller.mp_run(**input_args):
        os.system("clear")
        
        print(obs)