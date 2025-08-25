import argparse
from colabdesign.mpnn import mk_mpnn_model
from Bio.PDB import PDBIO, MMCIFParser
import pandas as pd

def int_to_chain(i,base=62):
    """
    int_to_chain(int,int) -> str
    Converts a positive integer to a chain ID. Chain IDs include uppercase
    characters, numbers, and optionally lowercase letters.
    i = a positive integer to convert
    base = the alphabet size to include. Typically 36 or 62.
    """
    if i < 0:
        raise ValueError("positive integers only")
    if base < 0 or 62 < base:
        raise ValueError("Invalid base")

    quot = int(i)//base
    rem = i%base
    if rem < 26:
        letter = chr( ord("A") + rem)
    elif rem < 36:
        letter = str( rem-26)
    else:
        letter = chr( ord("a") + rem - 36)
    if quot == 0:
        return letter
    else:
        return int_to_chain(quot-1,base) + letter

class OutOfChainsError(Exception): pass
def rename_chains(structure):
    """Renames chains to be one-letter chains
    
    Existing one-letter chains will be kept. Multi-letter chains will be truncated
    or renamed to the next available letter of the alphabet.
    
    If more than 62 chains are present in the structure, raises an OutOfChainsError
    
    Returns a map between new and old chain IDs, as well as modifying the input structure
    """
    next_chain = 0 #
    # single-letters stay the same
    chainmap = {c.id:c.id for c in structure.get_chains() if len(c.id) == 1}
    for o in structure.get_chains():
        if len(o.id) != 1:
            if o.id[0] not in chainmap:
                chainmap[o.id[0]] = o.id
                o.id = o.id[0]
            else:
                c = int_to_chain(next_chain)
                while c in chainmap:
                    next_chain += 1
                    c = int_to_chain(next_chain)
                    if next_chain >= 62:
                        raise OutOfChainsError()
                chainmap[c] = o.id
                o.id = c
    return chainmap

def run_mpnn(pdb_path, chains, out_dir, homooligomer=False, fix_pos=None, inverse=False, rm_aa=None, num_seqs=32, sampling_temp=0.1, model_name="v_48_002"):
    print(f"Loading MPNN {model_name}...")
    mpnn_model = mk_mpnn_model(model_name)
    print(f"MPNN {model_name} loaded.")

    print(f"Preparing inputs...")
    if pdb_path.endswith(".cif"):
        name = pdb_path.split("/")[-1].split(".")[0]
        
        parser = MMCIFParser()
        
        structure = parser.get_structure(name, pdb_path)
        
        try:
            chainmap = rename_chains(structure)
        except OutOfChainsError:
            print("Too many chains to represent in PDB format")
            return
    
        
        pdbio = PDBIO(use_model_flag=1)
        pdbio.set_structure(structure)
        pdbio.save(f"{out_dir}/{name}.pdb")
        
        pdb_path = f"{out_dir}/{name}.pdb"
    
    mpnn_model.prep_inputs(pdb_filename=pdb_path,
                            chain=chains, homooligomer=homooligomer,
                            fix_pos=fix_pos, inverse=inverse,
                            rm_aa=rm_aa, verbose=True)
    print(f"Sampling sequences...")
    out = mpnn_model.sample(num=int(num_seqs) // 32, batch=32,
                            temperature=float(sampling_temp),
                            rescore=homooligomer)

    with open(f'{out_dir}/designs.fasta', "w") as fasta:
        for n in range(int(num_seqs)):
            print(f"(design {n}) score:{out['score'][n]:.3f} seqid:{out['seqid'][n]:.3f}")
            line = f'>score:{out["score"][n]:.3f}_seqid:{out["seqid"][n]:.3f}\n{out["seq"][n]}'
            fasta.write(line + "\n")

    labels = ["score", "seqid", "seq"]
    data = [[out[k][n] for k in labels] for n in range(int(num_seqs))]

    summary_path = f'{out_dir}/mpnn_results.csv'

    # rename seq to protein_sequence
    labels[2] = "protein_sequence"
    
    df = pd.DataFrame(data, columns=labels)
    df.to_csv(summary_path, index=None)

def get_args():
    paser = argparse.ArgumentParser()
    paser.add_argument("--pdb_path", type=str, required=True)
    paser.add_argument("--chains", type=str, default="A")
    paser.add_argument("--out_dir", type=str, required=True)
    paser.add_argument("--homooligomer", type=bool, default=False)
    paser.add_argument("--fix_pos", type=str, default=None)
    paser.add_argument("--inverse", type=bool, default=False)
    paser.add_argument("--protein_sequence", type=str, default=None)
    paser.add_argument("--num_seqs", type=int, default=32)
    paser.add_argument("--sampling_temp", type=float, default=0.1)
    paser.add_argument("--model_name", type=str, default="v_48_002")
    return paser.parse_args()

def main(args):
    print(args.pdb_path)
    run_mpnn(args.pdb_path, args.chains, args.out_dir, args.homooligomer, args.fix_pos, args.inverse, args.protein_sequence, args.num_seqs, args.sampling_temp, args.model_name)
    
if __name__ == "__main__":
    """
    EXAMPLE:
        python command.py --pdb_path /root/ProtAgent/examples/pdb/diffab/3QHF_Fv.pdb \
                          --chains H \
                          --out_dir .
    """
    args = get_args()
    main(args)