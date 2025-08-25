import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import os
import datetime
from Bio import PDB

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(__file__)

@register_tool
class GetChainSequence(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/get_chain_sequence", **kwargs):
        """
        Initializes the GetChainSequence tool wrapper.
        """
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        self.tool_name = self.config.document["tool_name"]

    def __call__(self, pdb_file: str, chain_id: str, output_format: str = "dict") -> dict:
        """
        Get amino acid sequence for a specific chain ID from PDB file
        
        Args:
            pdb_file (str): Path to PDB file
            chain_id (str): Chain ID to extract sequence from
            output_format (str): Output format ("dict", "fasta", or "sequence_only")
        
        Returns:
            dict: Contains chain sequence information
        """
        try:
            # --- Input Validation ---
            pdb_abs_path = os.path.join(self.out_dir, pdb_file) if not os.path.isabs(pdb_file) else pdb_file
            
            if not os.path.exists(pdb_abs_path):
                return {"error": f"PDB file not found: {pdb_file}"}
            
            start_time = datetime.datetime.now()
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            
            save_dir = f"{self.out_dir}/get_chain_sequence/{timestamp}"
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # Write processing information to log file
            with open(self.log_path, "w") as log_file:
                log_file.write(f"Processing PDB file: {pdb_file}\n")
                log_file.write(f"Extracting sequence for chain: {chain_id}\n")
                log_file.write(f"Output format: {output_format}\n")
                log_file.write(f"Started at: {start_time}\n\n")
            
            # Parse PDB file
            parser = PDB.PDBParser(QUIET=True)
            structure = parser.get_structure('structure', pdb_abs_path)
            
            # Find the specified chain
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
            
            # Extract sequence and residue information
            sequence = ""
            residue_numbers = []
            residue_names = []
            
            for residue in chain:
                if PDB.is_aa(residue):  # Only standard amino acids
                    residue_numbers.append(residue.id[1])
                    residue_names.append(residue.resname)
                    # Convert three-letter code to one-letter code
                    aa3to1 = {
                        'ALA': 'A', 'CYS': 'C', 'ASP': 'D', 'GLU': 'E', 'PHE': 'F',
                        'GLY': 'G', 'HIS': 'H', 'ILE': 'I', 'LYS': 'K', 'LEU': 'L',
                        'MET': 'M', 'ASN': 'N', 'PRO': 'P', 'GLN': 'Q', 'ARG': 'R',
                        'SER': 'S', 'THR': 'T', 'VAL': 'V', 'TRP': 'W', 'TYR': 'Y'
                    }
                    if residue.resname in aa3to1:
                        sequence += aa3to1[residue.resname]
                    else:
                        sequence += 'X'  # Unknown amino acid
            
            duration = (datetime.datetime.now() - start_time).total_seconds()
            
            # Update log file with results
            with open(self.log_path, "a") as log_file:
                log_file.write(f"Successfully extracted sequence for chain {chain_id}\n")
                log_file.write(f"Sequence length: {len(sequence)} amino acids\n")
                log_file.write(f"Sequence: {sequence}\n")
                log_file.write(f"Processing completed in {duration:.3f} seconds\n")
            
            # Prepare results based on output format
            if output_format == "dict":
                result = {
                    "chain_id": chain_id,
                    "sequence": sequence,
                    "length": len(sequence),
                    "duration": duration
                }
            
            elif output_format == "fasta":
                fasta_content = f">{chain_id}\n{sequence}\n"
                output_file = os.path.join(save_dir, f"chain_{chain_id}_sequence.fasta")
                with open(output_file, 'w') as f:
                    f.write(fasta_content)
                
                result = {
                    "chain_id": chain_id,
                    "sequence": sequence,
                    "length": len(sequence),
                    "output_format": "fasta",
                    "output_content": fasta_content,
                    "output_file": output_file.replace(f"{self.out_dir}/", "", 1),
                    "duration": duration
                }
            
            elif output_format == "sequence_only":
                output_file = os.path.join(save_dir, f"chain_{chain_id}_sequence.txt")
                with open(output_file, 'w') as f:
                    f.write(sequence)
                
                result = {
                    "chain_id": chain_id,
                    "sequence": sequence,
                    "length": len(sequence),
                    "output_format": "sequence_only",
                    "output_content": sequence,
                    "output_file": output_file.replace(f"{self.out_dir}/", "", 1),
                    "duration": duration
                }
            
            else:
                return {"error": f"Invalid output_format: {output_format}. Must be 'dict', 'fasta', or 'sequence_only'"}
            
            return result
            
        except Exception as e:
            return {"error": f"Failed to extract chain sequence: {str(e)}"}

if __name__ == '__main__':
    tool = GetChainSequence()
    
    input_args = {
        "pdb_file": "example/query_example.pdb",
        "chain_id": "A",
        "output_format": "dict"
    }
    
    for obs in tool.mp_run(**input_args):
        os.system("clear")
        print(obs) 