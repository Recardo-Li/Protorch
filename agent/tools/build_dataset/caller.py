import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from Bio import SeqIO

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(__file__)


@register_tool
class BuildDataset(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/build_dataset", **kwargs):
        """
        Initializes the BuildDataset tool wrapper.
        """
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        self.tool_name = self.config.document["tool_name"]
    
    def __call__(self, fasta_files: list, train_ratio: float = 0.7, 
                 val_ratio: float = 0.15, test_ratio: float = 0.15) -> dict:
        """
        Creates classification dataset from FASTA files and splits into train/val/test sets.
        
        Args:
            fasta_files (list): List of FASTA file paths (relative to out_dir)
            train_ratio (float): Ratio for training set
            val_ratio (float): Ratio for validation set  
            test_ratio (float): Ratio for test set
            
        Returns:
            dict: A dictionary containing dataset paths and statistics
        """
        # --- Input Validation ---
        if not fasta_files:
            return {"error": "No FASTA files provided"}
        
        # Convert relative paths to absolute paths
        fasta_abs_paths = []
        for fasta_file in fasta_files:
            if not os.path.isabs(fasta_file):
                abs_fasta_file = os.path.join(self.out_dir, fasta_file)
            else:
                abs_fasta_file = fasta_file
            fasta_abs_paths.append(abs_fasta_file)
        
        # Validate all files exist
        for fasta_path in fasta_abs_paths:
            if not os.path.exists(fasta_path):
                return {"error": f"FASTA file not found: {fasta_path}"}
        
        start_time = datetime.datetime.now()
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        save_dir = f"{self.out_dir}/build_dataset/{timestamp}"
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        try:
            # Import and call command module
            from agent.tools.build_dataset.command import BuildDatasetCommand
            
            command = BuildDatasetCommand(save_dir)
            
            # Create dataset
            dataset_file = command.create_classification_dataset(
                fasta_abs_paths
            )
            
            # Split dataset
            split_dataset = command.split_dataset_simple(
                dataset_file, train_ratio, val_ratio, test_ratio
            )
            
            # Calculate statistics
            df = pd.read_csv(split_dataset)
            train_df = df[df['stage'] == 'train']
            val_df = df[df['stage'] == 'val']
            test_df = df[df['stage'] == 'test']
            
            duration = (datetime.datetime.now() - start_time).total_seconds()
            
            result = {
                "dataset_path": split_dataset.replace(f"{self.out_dir}/", "", 1),
                "train_count": len(train_df),
                "val_count": len(val_df), 
                "test_count": len(test_df),
                "total_sequences": len(df),
                "num_classes": len(df['label'].unique()),
                "class_distribution": df['label'].value_counts().to_dict(),
                "duration": duration
            }
            
            return result
            
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


if __name__ == '__main__':
    caller = BuildDataset(BASE_DIR)
    
    input_args = {
        "fasta_files": ["example/class0.fasta", "example/class1.fasta"],
        "train_ratio": 0.7,
        "val_ratio": 0.15,
        "test_ratio": 0.15
    }
    
    for obs in caller.mp_run(**input_args):
        os.system("clear")
        print(obs) 