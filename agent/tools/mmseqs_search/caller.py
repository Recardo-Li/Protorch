import sys
import time

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
class MMSeqsSearch(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/mmseqs_search", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, query_fasta_path, target_fasta_path, identity=0.5) -> dict:
        if not os.path.isabs(query_fasta_path):
            query_fasta_path = os.path.join(self.out_dir, query_fasta_path)
        if not os.path.isabs(target_fasta_path):
            target_fasta_path = os.path.join(self.out_dir, target_fasta_path)
        
        start = datetime.datetime.now()
        now = start.strftime("%Y%m%d_%H%M")
        save_dir = f"{self.out_dir}/mmseqs_search/{now}"
        os.makedirs(save_dir, exist_ok=True)
        
        mmseqs_path = self.config["bin"]
        
        script_path = f'{BASE_DIR}/{self.config["script"]}'

        result_path = f"{save_dir}/{os.path.splitext(os.path.basename(target_fasta_path))[0]}_filtered{str(int(identity*100))}.fasta"

        script_args = [mmseqs_path, query_fasta_path, target_fasta_path, result_path, str(identity)]
        
        cmd = [f"cd {ROOT_DIR} && "]+ [script_path] + script_args
        cmd = " ".join(cmd)
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        
        try:
            os.system(cmd)
            
            # 导入过滤序列模块
            import sys
            sys.path.insert(0, BASE_DIR)
            from filter_sequences import filter_sequences
            
            # 调用过滤函数，获取统计信息
            matched_ids_path = f"{result_path}.matched_ids"
            original_count, filtered_count, removed_count = filter_sequences(
                target_fasta_path, matched_ids_path, result_path
            )
            
            spend_time = (datetime.datetime.now() - start).total_seconds()
            return {
                "filtered_fasta_path": result_path[len(self.out_dir)+1:], 
                "target_sequences_remaining_number": filtered_count,
                "target_sequences_removed_number": removed_count,
                "duration": spend_time
            }
        
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    # Test
    mmseqs_search = MMSeqsSearch(BASE_DIR)
    
    input_args = {
        "query_fasta_path": "example/fasta1.fasta",
        "target_fasta_path": "example/fasta2.fasta",
        "identity": 0.5
    }

    print("=== MMSeqs Search Tool Test ===")
    print(f"Query file: {input_args['query_fasta_path']}")
    print(f"Target file: {input_args['target_fasta_path']}")
    print(f"Identity threshold: {input_args['identity']}")
    print("\nRunning MMSeqs search...")

    for obs in mmseqs_search.mp_run(**input_args):
        os.system("clear")
        print("=== Results ===")
        print(obs)

        # mmseqs_search.terminate()