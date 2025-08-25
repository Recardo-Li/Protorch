from Bio import PDB
import argparse

def read_pdb_sequences(pdb_file):
    """
    Reads a PDB file and extracts sequences of all protein chains.
    Returns a list of tuples containing (chain_id, sequence).
    """
    parser = PDB.PDBParser(QUIET=True) if pdb_file.endswith('.pdb') else PDB.MMCIFParser(QUIET=True)
    structure = parser.get_structure('temp', pdb_file)
    chain_sequences = []
    
    for model in structure:
        for chain in model:
            for residue in chain:
                if residue.id[0] == ' ' and PDB.is_aa(residue, standard=True):
                    # Get the amino acid sequence
                    seq = residue.get_resname()
                    if not chain_sequences or chain_sequences[-1][0] != chain.id:
                        chain_sequences.append((chain.id, seq))
                    else:
                        chain_sequences[-1] = (chain.id, chain_sequences[-1][1] + seq)
    return chain_sequences

def main():
    """
    Main function that handles command-line arguments and prints the sequences.
    """
    parser = argparse.ArgumentParser(description='Extract protein sequences from a PDB file.')
    parser.add_argument('--pdb_file', type=str, required=True,
                        help='Path to the input PDB file.')
    
    args = parser.parse_args()
    
    sequences = read_pdb_sequences(args.pdb_file)
    
    if len(sequences) == 0:
        raise ValueError("No protein chains found in the PDB file.")
    if len(sequences) > 1:
        raise ValueError("Multiple protein chains found in the PDB file. Please provide a PDB file with a single chain.")
    for chain_id, sequence in sequences:
        print(f"Sequence: {sequence}")
        print(f"Length: {len(sequence)}")

if __name__ == "__main__":
    """
    EXAMPLE:
    python command.py --pdb_file example/1A2B.pdb
    """
    main()
