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
class HHMake(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/hhmake", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "hhmake"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.config["example_output"] = self.config["example_output"][tool_name]
        self.tool_name = tool_name
    
    def __call__(self, msa_file) -> dict:
        msa_file = f"{self.out_dir}/{msa_file}"
        start_time = datetime.datetime.now()
        now = start_time.strftime("%Y%m%d_%H%M")
        save_dir = f"{self.out_dir}/hhmake/{now}"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        save_path = f"{save_dir}/{os.path.basename(msa_file).split('.')[0]}.hmm"
        
        # Call the hhmake
        cmd = f"{ROOT_DIR}/{self.config.HHmake} -i '{msa_file}' -o '{save_path}' > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)  
            end_time = datetime.datetime.now()
            spend_time = (end_time - start_time).total_seconds()
            if os.path.exists(save_path):
                return {"hmm_file": save_path[len(self.out_dir)+1:], "duration": spend_time}
            
            else:
                raise Exception("HHmake encountered an error. Please check your inputs and options.")
        
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    hhmake = HHMake(BASE_DIR)
    
    input_args = {
        "msa_file": f"example/protein_sequence.a3m",
    }
    for obs in hhmake.mp_run(**input_args):
        os.system("clear")
        print(obs)

    