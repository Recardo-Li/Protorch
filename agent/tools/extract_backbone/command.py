import os
import argparse
from Bio.PDB import PDBParser, MMCIFParser, Select, PDBIO, is_aa

class BackboneSelect(Select):
    """Selects protein backbone atoms (N, CA, C, O) from standard amino acids."""
    def accept_residue(self, residue):
        return is_aa(residue)
    
    def accept_atom(self, atom):
        return atom.get_name() in {'N', 'CA', 'C', 'O'}

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Extract protein backbone atoms from a structure file.')
    parser.add_argument('--structure_path', required=True, type=str,
                       help='Input structure file path (supports PDB and mmCIF formats)')
    parser.add_argument('--output', '-o', type=str,
                       help='Output PDB file path. Default: <input_filename>_backbone.pdb')
    
    args = parser.parse_args()
    
    # Determine output path
    if not args.output:
        base_name = os.path.splitext(args.structure_path)[0]
        args.output = f"{base_name}_backbone.pdb"
    
    # Initialize appropriate parser based on file extension
    file_ext = os.path.splitext(args.structure_path)[1].lower()
    if file_ext in ('.cif', '.mmcif'):
        parser = MMCIFParser()
    else:  # Default to PDB parser
        parser = PDBParser()

    # Parse structure with error handling
    try:
        structure = parser.get_structure('protein', args.structure_path)
    except Exception as e:
        raise ValueError(f"Error parsing structure file: {e}")

    # Save filtered structure
    io = PDBIO()
    io.set_structure(structure)
    io.save(args.output, BackboneSelect())

    print(f"Backbone structure saved to: {args.output}")

if __name__ == "__main__":
    """
    Example Usage:
    python script.py --structure_path input.pdb -o output.pdb
    python script.py --structure_path structure.cif
    """
    main()