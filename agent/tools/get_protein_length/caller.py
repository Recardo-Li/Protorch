import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import os
import datetime
from Bio import PDB
from typing import Optional

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(__file__)

@register_tool
class GetProteinLength(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/get_protein_length", **kwargs):
        """
        Initializes the GetProteinLength tool wrapper.
        """
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        self.tool_name = self.config.document["tool_name"]

    def __call__(self, pdb_file: str, chain_id: Optional[str] = None) -> dict:
        """
        Calculate protein length from PDB file
        
        Args:
            pdb_file (str): Path to PDB file
            chain_id (str, optional): Specific chain ID to analyze (optional, if None analyzes all chains)
        
        Returns:
            dict: Contains protein length information
        """
        try:
            # --- Input Validation ---
            pdb_abs_path = os.path.join(self.out_dir, pdb_file) if not os.path.isabs(pdb_file) else pdb_file
            
            if not os.path.exists(pdb_abs_path):
                return {"error": f"PDB file not found: {pdb_file}"}
            
            start_time = datetime.datetime.now()
            
            # Write processing information to log file
            with open(self.log_path, "w") as log_file:
                log_file.write(f"Processing PDB file: {pdb_file}\n")
                if chain_id is not None:
                    log_file.write(f"Analyzing specific chain: {chain_id}\n")
                else:
                    log_file.write("Analyzing all chains\n")
                log_file.write(f"Started at: {start_time}\n\n")
            
            # Parse PDB file
            parser = PDB.PDBParser(QUIET=True)
            structure = parser.get_structure('structure', pdb_abs_path)
            
            if chain_id is not None:
                # Analyze specific chain
                chain = None
                for model in structure:
                    if chain_id in model:
                        chain = model[chain_id]
                        break
                
                if chain is None:
                    available_chains = []
                    for model in structure:
                        available_chains.extend([c.id for c in model])
                    return {"error": f"Chain '{chain_id}' not found in PDB file. Available chains: {list(set(available_chains))}"}
                
                # Count amino acid residues in the specific chain
                length = sum(1 for residue in chain if PDB.is_aa(residue))
                
                duration = (datetime.datetime.now() - start_time).total_seconds()
                
                # Update log file with results
                with open(self.log_path, "a") as log_file:
                    log_file.write(f"Chain {chain_id} length: {length} amino acids\n")
                    log_file.write(f"Processing completed in {duration:.3f} seconds\n")
                
                result = {
                    "chain_id": chain_id,
                    "length": length,
                    "duration": duration
                }
                
            else:
                # Analyze all chains
                chain_lengths = {}
                total_length = 0
                chain_count = 0
                
                for model in structure:
                    for chain in model:
                        chain_id_current = chain.id
                        # Count amino acid residues in this chain
                        length = sum(1 for residue in chain if PDB.is_aa(residue))
                        
                        if length > 0:  # Only include chains with amino acids
                            chain_lengths[chain_id_current] = length
                            total_length += length
                            chain_count += 1
                
                duration = (datetime.datetime.now() - start_time).total_seconds()
                
                # Update log file with results
                with open(self.log_path, "a") as log_file:
                    log_file.write(f"Found {chain_count} protein chains\n")
                    for cid, length in chain_lengths.items():
                        log_file.write(f"Chain {cid}: {length} amino acids\n")
                    log_file.write(f"Total protein length: {total_length} amino acids\n")
                    log_file.write(f"Processing completed in {duration:.3f} seconds\n")
                
                result = {
                    "chain_lengths": chain_lengths,
                    "total_length": total_length,
                    "chain_count": chain_count,
                    "duration": duration
                }
            
            return result
            
        except Exception as e:
            return {"error": f"Failed to process PDB file: {str(e)}"}

if __name__ == '__main__':
    tool = GetProteinLength()
    
    input_args = {
        "pdb_file": "example/query_example.pdb"
    }
    
    for obs in tool.mp_run(**input_args):
        os.system("clear")
        print(obs) 