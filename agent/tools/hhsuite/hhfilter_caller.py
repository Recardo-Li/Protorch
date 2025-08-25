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
class HHFilter(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/hhfilter", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        tool_name = "hhfilter"
        for doc in self.config["document"]:
            if doc["tool_name"] == tool_name:
                self.config["document"] = doc
                break
        self.config["example_output"] = self.config["example_output"][tool_name]
        self.tool_name = tool_name
    
    def __call__(self, input_msa, id=90, cov=50, diff=1000) -> dict:
        input_msa = f"{self.out_dir}/{input_msa}"
        
        origin_seq_num = self._parse_a3m_for_sequence_count(input_msa)
        
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        save_dir = f"{self.out_dir}/hhfilter/{now}"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        save_path = f"{save_dir}/{os.path.basename(input_msa).split('.')[0]}_filtered-{id}.a3m"

        # Call the hhfilter
        cmd = f"{ROOT_DIR}/{self.config.HHfilter} -i '{input_msa}' -o '{save_path}' -id {id} -diff {diff} -cov {cov} > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)  
            if os.path.exists(save_path):
                results_num = self._parse_a3m_for_sequence_count(save_path)
                spend_time = (datetime.datetime.now() - start).total_seconds()
                return {"filtered_msa": save_path[len(self.out_dir)+1:],
                    "origin_num": origin_seq_num,
                    "results_num": results_num, "duration": spend_time}
            else:
                return {"error": "HHfilter encountered an error. Please check your inputs and options."}
        
        except Exception as e:
            return {"error": str(e)}

    def _parse_a3m_for_sequence_count(self, a3m_path: str) -> int:
        """
        Parses an A3M file to count the number of sequences.
        This is done by counting lines that start with '>'.
        """
        count = 0
        try:
            with open(a3m_path, "r") as f:
                for line in f:
                    if line.startswith(">"):
                        count += 1
        except IOError as e:
            print(f"Warning: Could not read A3M file '{a3m_path}' to count sequences. Error: {e}")
        return count


if __name__ == '__main__':
    # Test
    hhfilter = HHFilter(BASE_DIR)
    
    input_args = {
        "input_msa": f"example/protein_sequence.a3m",
        "id": 90,
        "cov": 50,
        "diff": 1000
    }
    for obs in hhfilter.mp_run(**input_args):
        os.system("clear")
        print(obs)
