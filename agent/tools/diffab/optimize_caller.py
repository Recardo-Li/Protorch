import sys
import time

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
class DiffAbOptimize(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/diffab_optimize", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        for doc in self.config["document"]:
            if doc["tool_name"] == "diffab_optimize":
                self.config["document"] = doc
                break
        self.tool_name = "diffab_optimize"
        
    def get_model_dir(self, config):
        if config == "abopt_singlecdr" or "codesign_single":
            return f"{ROOT_DIR}/modelhub/DiffAb/codesign_single.pt"
        if config == "codesign_multicdrs":
            return f"{ROOT_DIR}/modelhub/DiffAb/codesign_multicdrs.pt"
        if config == "fixbb":
            return f"{ROOT_DIR}/modelhub/DiffAb/fixbb.pt"
        if config == "strpred":
            return f"{ROOT_DIR}/modelhub/DiffAb/structure_pred.pt"
        
    def __call__(self, antigen_antibody_structure, diffab_config="codesign_multicdrs", num_samples=10, relax_distance=6, repeats=3) -> dict:
        antigen_antibody_structure = f"{self.out_dir}/{antigen_antibody_structure}"
        
        model_dir = self.get_model_dir(diffab_config)
        diffab_config = f"{BASE_DIR}/diffab/configs/{diffab_config}.yml"
        
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M")
        
        out_root = f"{self.out_dir}/diffab_optimize/{now}"
        os.makedirs(out_root, exist_ok=True)
        tmp_root = f"{out_root}/tmp"
        os.makedirs(tmp_root, exist_ok=True)
        
        cmd = f"bash {BASE_DIR}/{self.config['script']['optimize']} env_name={self.config['env_name']} \
                                                        root_dir={ROOT_DIR} \
                                                        pdb_path={antigen_antibody_structure} \
                                                        out_root={out_root} \
                                                        config={diffab_config} \
                                                        num_samples={num_samples} \
                                                        model_dir={model_dir} \
                                                        relax_distance={relax_distance} \
                                                        repeats={repeats}"
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)
            
            if os.path.exists(f"{out_root}/final_score.json"):
                with open(f"{out_root}/final_score.json", "r") as f:
                    final_dict = json.load(f)
                return {"result_pdb": f"{out_root[len(self.out_dir)+1:]}/final_relaxed.pdb",
                        "binding_energy": round(final_dict["dG_separated"], 2),
                        "buried_sasa": round(final_dict["dSASA_int"], 2),
                        "shape_complementarity": round(final_dict["sc_value"], 2)}
            else:
                return {"error": "Failed to run DiffAbOptimize. No output directory found."}
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    diffab_antigen_antibody = DiffAbOptimize(out_dir="/root/ProtAgent/agent/tools/diffab/example")

    input_args = {
        "antigen_antibody_structure": "optimize_case.pdb",
        "diffab_config": "codesign_multicdrs",
        "relax_distance":4, 
        "repeats":1
        }
    
    for obs in diffab_antigen_antibody.mp_run(**input_args):
        os.system("clear")
        print(obs)

    