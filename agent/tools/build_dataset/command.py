import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from Bio import SeqIO


class BuildDatasetCommand:
    def __init__(self, save_dir: str):
        """
        Initialize BuildDatasetCommand with save directory.
        
        Args:
            save_dir (str): Directory to save output files
        """
        self.save_dir = save_dir
    
    def create_classification_dataset(self, fasta_files: list):
        """
        Create classification dataset from multiple FASTA files.
        
        Args:
            fasta_files (list): List of absolute paths to FASTA files
            
        Returns:
            str: Path to created dataset CSV file
        """
        sequences = []
        labels = []
        
        # Use list index as label (0, 1, 2, ...)
        for i, fasta_file in enumerate(fasta_files):
            filename = os.path.basename(fasta_file)
            label = i  # Use index as label
            
            # Read sequences from FASTA file
            for record in SeqIO.parse(fasta_file, "fasta"):
                sequences.append(str(record.seq))
                labels.append(label)
        
        # Create dataset file
        dataset_file = os.path.join(self.save_dir, "classification_dataset.csv")
        df = pd.DataFrame({
            'sequence': sequences,
            'label': labels,
            'stage': 'all'  # Initial stage marked as all
        })
        df.to_csv(dataset_file, index=False)
        
        return dataset_file
    
    def split_dataset_simple(self, dataset_file: str, train_ratio: float, 
                           val_ratio: float, test_ratio: float):
        """
        Split dataset into train/val/test sets.
        
        Args:
            dataset_file (str): Path to dataset CSV file
            train_ratio (float): Ratio for training set
            val_ratio (float): Ratio for validation set
            test_ratio (float): Ratio for test set
            
        Returns:
            str: Path to split dataset CSV file
        """
        df = pd.read_csv(dataset_file)
        
        # Validate ratios
        total_ratio = train_ratio + val_ratio + test_ratio
        if abs(total_ratio - 1.0) > 1e-6:
            raise ValueError(f"Ratios must sum to 1.0, got {total_ratio}")
        
        # Shuffle the dataset
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)
        
        n_total = len(df)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * val_ratio)
        
        # Split dataset
        train_df = df[:n_train].copy()
        val_df = df[n_train:n_train+n_val].copy()
        test_df = df[n_train+n_val:].copy()
        
        # Add stage labels
        train_df['stage'] = 'train'
        val_df['stage'] = 'valid'
        test_df['stage'] = 'test'
        
        # Combine all splits
        final_df = pd.concat([train_df, val_df, test_df], ignore_index=True)
        
        # Save split dataset
        split_file = dataset_file.replace('.csv', '_split.csv')
        final_df.to_csv(split_file, index=False)
        
        return split_file
    
    def split_dataset_stratified(self, dataset_file: str, train_ratio: float,
                               val_ratio: float, test_ratio: float):
        """
        Split dataset with stratified sampling to maintain label distribution.
        
        Args:
            dataset_file (str): Path to dataset CSV file
            train_ratio (float): Ratio for training set
            val_ratio (float): Ratio for validation set
            test_ratio (float): Ratio for test set
            
        Returns:
            str: Path to split dataset CSV file
        """
        df = pd.read_csv(dataset_file)
        
        # Validate ratios
        total_ratio = train_ratio + val_ratio + test_ratio
        if abs(total_ratio - 1.0) > 1e-6:
            raise ValueError(f"Ratios must sum to 1.0, got {total_ratio}")
        
        # Check if we have enough samples per class
        label_counts = df['label'].value_counts()
        min_samples = label_counts.min()
        
        if min_samples < 3:
            # Not enough samples for stratified split, use simple split
            return self.split_dataset_simple(dataset_file, train_ratio, val_ratio, test_ratio)
        
        X = df['sequence'].values
        y = df['label'].values
        
        # Stratified split to maintain label distribution
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=(1-train_ratio), random_state=42, stratify=y
        )
        
        relative_val_size = val_ratio / (val_ratio + test_ratio)
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=(1-relative_val_size), random_state=42, stratify=y_temp
        )
        
        train_df = pd.DataFrame({'sequence': X_train, 'label': y_train, 'stage': 'train'})
        val_df = pd.DataFrame({'sequence': X_val, 'label': y_val, 'stage': 'val'})
        test_df = pd.DataFrame({'sequence': X_test, 'label': y_test, 'stage': 'test'})
        
        final_df = pd.concat([train_df, val_df, test_df], ignore_index=True)
        
        split_file = dataset_file.replace('.csv', '_split.csv')
        final_df.to_csv(split_file, index=False)
        
        return split_file 