import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import os
import datetime
from Bio import PDB
from Bio.PDB.PDBIO import PDBIO
from typing import Optional

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool

BASE_DIR = os.path.dirname(__file__)

@register_tool
class ExtractPeptide(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/extract_peptide", **kwargs):
        """
        Initializes the ExtractPeptide tool wrapper.
        """
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
        self.tool_name = self.config.document["tool_name"]

    def __call__(self, pdb_file: str, start_residue: int, end_residue: int, chain_id: str = "A", output_filename: Optional[str] = None) -> dict:
        """
        Extract peptide from protein structure based on residue coordinates
        
        Args:
            pdb_file (str): Path to PDB file
            start_residue (int): Starting residue number (inclusive)
            end_residue (int): Ending residue number (inclusive) 
            chain_id (str): Chain ID to extract from (default "A")
            output_filename (str, optional): Name for output PDB file (optional)
        
        Returns:
            dict: Contains extracted peptide information and output path
        """
        try:
            # --- Input Validation ---
            pdb_abs_path = os.path.join(self.out_dir, pdb_file) if not os.path.isabs(pdb_file) else pdb_file
            
            if not os.path.exists(pdb_abs_path):
                return {"error": f"PDB file not found: {pdb_file}"}
            
            # Validate residue range
            if start_residue > end_residue:
                return {"error": "Start residue must be less than or equal to end residue"}
            
            start_time = datetime.datetime.now()
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            
            save_dir = f"{self.out_dir}/extract_peptide/{timestamp}"
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # Write processing information to log file
            with open(self.log_path, "w") as log_file:
                log_file.write(f"Processing PDB file: {pdb_file}\n")
                log_file.write(f"Extracting chain {chain_id}, residues {start_residue}-{end_residue}\n")
                if output_filename:
                    log_file.write(f"Output filename: {output_filename}\n")
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
            
            # Check if the specified range contains any amino acid residues
            chain_residues = [residue.id[1] for residue in chain if PDB.is_aa(residue)]
            chain_residues.sort()
            
            if not chain_residues:
                error_msg = f"No amino acid residues found in chain {chain_id}"
                with open(self.log_path, "a") as log_file:
                    log_file.write(f"ERROR: {error_msg}\n")
                return {"error": error_msg}
            
            # Check if the specified range overlaps with actual residues
            residues_in_range = [res_num for res_num in chain_residues if start_residue <= res_num <= end_residue]
            
            if not residues_in_range:
                first_residue = chain_residues[0]
                last_residue = chain_residues[-1]
                error_msg = f"No residues found in range {start_residue}-{end_residue}. Chain {chain_id} contains residues from {first_residue} to {last_residue}"
                
                with open(self.log_path, "a") as log_file:
                    log_file.write(f"ERROR: {error_msg}\n")
                    log_file.write(f"Available residues in chain {chain_id}: {first_residue}-{last_residue}\n")
                    log_file.write(f"Requested range: {start_residue}-{end_residue}\n")
                    
                return {"error": error_msg}
            
            # Log the actual residues that will be extracted
            with open(self.log_path, "a") as log_file:
                log_file.write(f"Found {len(residues_in_range)} residues in range {start_residue}-{end_residue}\n")
                log_file.write(f"Residues to extract: {residues_in_range}\n\n")
            
            # Create a new structure for the peptide
            class ResidueSelect:
                def __init__(self, start_res, end_res, target_chain):
                    self.start_res = start_res
                    self.end_res = end_res
                    self.target_chain = target_chain
                
                def accept_residue(self, residue):
                    return (residue.get_parent().id == self.target_chain and 
                           self.start_res <= residue.id[1] <= self.end_res and
                           PDB.is_aa(residue))
                
                def accept_chain(self, chain):
                    return chain.id == self.target_chain
                
                def accept_model(self, model):
                    return True
                
                def accept_atom(self, atom):
                    return True
            
            # Generate output filename if not provided
            if output_filename is None:
                base_name = os.path.splitext(os.path.basename(pdb_file))[0]
                output_filename = f"{base_name}_peptide_{chain_id}_{start_residue}_{end_residue}.pdb"
            
            output_path = os.path.join(save_dir, output_filename)
            
            # Extract and save peptide
            io = PDBIO()
            io.set_structure(structure)
            selector = ResidueSelect(start_residue, end_residue, chain_id)
            io.save(output_path, selector)
            
            # Check if any residues were extracted
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                return {"error": f"No residues found in the specified range {start_residue}-{end_residue} for chain {chain_id}"}
            
            # Extract sequence from the selected residues
            sequence = ""
            extracted_residues = 0
            
            # Amino acid mapping
            aa3to1 = {
                'ALA': 'A', 'CYS': 'C', 'ASP': 'D', 'GLU': 'E', 'PHE': 'F',
                'GLY': 'G', 'HIS': 'H', 'ILE': 'I', 'LYS': 'K', 'LEU': 'L',
                'MET': 'M', 'ASN': 'N', 'PRO': 'P', 'GLN': 'Q', 'ARG': 'R',
                'SER': 'S', 'THR': 'T', 'VAL': 'V', 'TRP': 'W', 'TYR': 'Y'
            }
            
            for residue in chain:
                if (start_residue <= residue.id[1] <= end_residue and PDB.is_aa(residue)):
                    extracted_residues += 1
                    if residue.resname in aa3to1:
                        sequence += aa3to1[residue.resname]
                    else:
                        sequence += 'X'  # Unknown amino acid
            
            duration = (datetime.datetime.now() - start_time).total_seconds()
            
            # Update log file with results
            with open(self.log_path, "a") as log_file:
                log_file.write(f"Extracted {extracted_residues} residues\n")
                log_file.write(f"Peptide sequence: {sequence}\n")
                log_file.write(f"Output saved to: {output_path}\n")
                log_file.write(f"Processing completed in {duration:.3f} seconds\n")
            
            result = {
                "peptide_sequence": sequence,
                "chain_id": chain_id,
                "output_file": output_path.replace(f"{self.out_dir}/", "", 1),
                "duration": duration
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Failed to extract peptide: {str(e)}"}

if __name__ == '__main__':
    tool = ExtractPeptide()
    
    input_args = {
        "pdb_file": "example/query_example.pdb",
        "start_residue": 322,
        "end_residue": 340,
        "chain_id": "A"
    }
    
    for obs in tool.mp_run(**input_args):
        os.system("clear")
        print(obs) 