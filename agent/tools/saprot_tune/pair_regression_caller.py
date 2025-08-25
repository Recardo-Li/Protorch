import os
import sys


ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import torch
import datetime

from agent.tools.saprot_tune.tune_caller import TuneCaller
from agent.tools.register import register_tool

torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)

HUGGINGFACE_ROOT = "/home/public/huggingface/"


@register_tool
class TunePairRegressionCaller(TuneCaller):
    def __init__(self, **kwargs):
        super().__init__("saprot_tune_pair_regression", **kwargs)

    def __call__(self, dataset, base_model="SaProt_35M", batch_size="Adaptive", max_epoch=10, learning_rate=1e-3) -> dict:
        dataset = f"{self.out_dir}/{dataset}"
        
        # Create save directory following the same pattern as other callers
        start_time = datetime.datetime.now()
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        work_dir = f"{self.out_dir}/saprot_tune_pair_regression/{timestamp}"
        os.makedirs(work_dir, exist_ok=True)
        
        # Copy dataset to work directory so the model saves there
        import shutil
        dataset_name = os.path.basename(dataset)
        work_dataset = f"{work_dir}/{dataset_name}"
        shutil.copy2(dataset, work_dataset)
        
        cmd_args = {
            "task_type": "pair_regression",
            "huggingface_path": f'{ROOT_DIR}/{self.config["saprot_root"]}/{base_model}_AF2',
            "dataset": work_dataset,
            "default_config_path": f'{BASE_DIR}/{self.config["default_config_path"]}',
            "batch_size": batch_size if type(batch_size) is str else int(batch_size),
            "max_epoch": int(max_epoch),
            "learning_rate": float(learning_rate)
        }
        
        cmd = f"{self.config['python']} {BASE_DIR}/command.py"
        for k, v in cmd_args.items():
            cmd += f" --{k} '{v}'"
        
        # Redirect the stdout and stderr to a log file
        cmd += f" > {self.log_path} 2>&1"
        os.system(cmd)
        
        # Parse metrics from log
        save_dir = None
        metrics = ["test_spearman", "test_R2", "test_pearson", "test_loss"]
        metrics_dict = self.log2metric(metrics)
        with open(self.log_path, "r") as r:
            for line in r:
                if line.startswith("Loaded best model from:"):
                    save_dir = line.split("Loaded best model from:")[1].strip()
                    break
        
        # Check if training was successful by looking for the model files
        model_files = ["adapter_config.json", "adapter_model.safetensors"]
        training_successful = save_dir and all(os.path.exists(f"{work_dir}/{save_dir}/{file}") for file in model_files)
        
        if not training_successful:
            return {"error": "Saprot pair regression tuning failed. Model files not found."}
        else:
            duration = (datetime.datetime.now() - start_time).total_seconds()
            return {"save_dir": f"saprot_tune_pair_regression/{timestamp}/{save_dir}",
                    "valid_metrics_curve": f"{work_dir}/{save_dir}/validation_metric_curve.jpg", 
                    "duration": duration,
                    **metrics_dict}
            
    def log2metric(self, metrics):
        metrics_dict = {}
        with open(self.log_path, "r") as r:
            for line in r:
                for metric in metrics:
                    if line.startswith(f"{metric}:"):
                        metrics_dict[metric] = float(line.split(f"{metric}:")[1].strip())
        return metrics_dict
    
if __name__ == "__main__":
    caller = TunePairRegressionCaller(out_dir=BASE_DIR)
    
    input_args = {
        "dataset": "example/[EXAMPLE][Pair AA][Regression].csv",
        "base_model": "SaProt_35M",
        "batch_size": 32,
        "max_epoch": 1,
        "learning_rate": 1e-3
    }

    for obs in caller.mp_run(**input_args):
        os.system("clear")
        
        print(obs)