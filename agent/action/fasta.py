import os
import time

from typing import List
from .config import get_temp_dir
from lagent.actions.base_action import BaseAction, tool_api
from Bio import SeqIO


class FastaOperator(BaseAction):
    """
    Ensemble operations for FASTA format file.
    """
    @tool_api
    def save(self, sequences: list) -> dict:
        """
        Save protein sequences to a FASTA file.

        Args:
            sequences (List[str]): Protein sequences to save

        Returns:
            dict:
                - save_path (str): Save path of the FASTA file
            or  - error (str): Error message
        """
        assert len(sequences) > 0, "Error: No sequences to save!"
        assert isinstance(sequences, list), "Error: 'sequences' must be a list!"
        
        save_path = f"{get_temp_dir()}/{time.time()}.fasta"
        with open(save_path, "w") as w:
            for i, sequence in enumerate(sequences):
                w.write(f">seq_{i}\n{sequence}\n")
                
        return {"save_path": save_path}
    
    @tool_api
    def load(self, fasta_path: str):
        """
        Load protein sequences from a FASTA file. Don't use this tool unless the user require seeing the sequences inside the fasta file.

        Args:
            fasta_path (str): Path to the FASTA file

        Returns:
            dict: Sequence information
                - sequences (str): Protein sequences
        """
        assert os.path.exists(fasta_path), f"Error: {fasta_path} does not exist!"
        
        sequences = ""
        for seq_record in SeqIO.parse(fasta_path, "fasta"):
            sequences += f">{seq_record.id}\n{seq_record.seq}\n"
                
        return {"sequence": sequences}
