import argparse
import asyncio
import datetime
import re
from gradio_client import Client
from Bio import PDB
import torch
from transformers import AutoTokenizer, EsmForProteinFolding
from transformers.models.esm.openfold_utils.protein import to_pdb, Protein as OFProtein
from transformers.models.esm.openfold_utils.feats import atom14_to_atom37
import time
import os
import requests

import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    

from data.utils.parse import get_chain_ids
from utils.foldseek_util import get_struc_seq
from agent.tools.esmfold.command import predict, load_model

three_to_one = {
    'ALA': 'A', 'CYS': 'C', 'ASP': 'D', 'GLU': 'E', 'PHE': 'F', 
    'GLY': 'G', 'HIS': 'H', 'ILE': 'I', 'LYS': 'K', 'LEU': 'L', 
    'MET': 'M', 'ASN': 'N', 'PRO': 'P', 'GLN': 'Q', 'ARG': 'R', 
    'SER': 'S', 'THR': 'T', 'VAL': 'V', 'TRP': 'W', 'TYR': 'Y'
}


def extract_aa_sequence(pdb_file_path):
    # Create a PDB parser
    parser = PDB.PDBParser(QUIET=True) if pdb_file_path.endswith('.pdb') else PDB.MMCIFParser(QUIET=True)
    
    # Read the PDB file
    structure = parser.get_structure('protein', pdb_file_path)
    
    # Extract the amino acid sequence
    sequence = []
    for model in structure:
        for chain in model:
            for residue in chain:
                # Check if the residue is an amino acid
                if PDB.is_aa(residue):
                    # Convert three-letter code to one-letter code and add to sequence
                    resname = residue.get_resname()
                    if resname in three_to_one:
                        sequence.append(three_to_one[resname])
    
    # Return the amino acid sequence as a string
    return ''.join(sequence)

def get_foldseek(pdb_path, foldseek_path):
    print(f"Start FoldSeek for {pdb_path}")
    
    chains = get_chain_ids(pdb_path)
    print(f"Found Chains: {chains}")
    
    seq_dict = get_struc_seq(foldseek_path, pdb_path, chains, process_id=0, plddt_mask=True, plddt_threshold=70.0)
    
    return seq_dict[chains[0]][1]

def id_args(uniprot_id, tmp_pdb_dir, foldseek_path):
    print(f"Start fetching protein sequence for {uniprot_id}")
    url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.fasta"
    requests_return = requests.get(url)
    splits = requests_return.text.split("\n")
    protein_sequence = "".join(splits[1:]).strip()
    print(f"Protein sequence fetched successfully. Found {len(protein_sequence)} amino acids")
    
    print(f"Start fetching protein structure for {uniprot_id}")
    url = f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb"
    save_path = f"{tmp_pdb_dir}/{uniprot_id}.pdb"
    wget = f"wget -q -o /dev/null {url} -O {save_path}"
    # Execute the command and output to /dev/null
    os.system(f"{wget}")
    print(f"Protein structure fetched successfully. Saved to {save_path}")

    protein_structure = save_path
    foldseek_str = get_foldseek(protein_structure, foldseek_path).lower()
    return protein_sequence, foldseek_str

def seq_args(protein_sequence, tmp_pdb_dir, esmfold_path, foldseek_path):
    print(f"Start loading ESMFold from {esmfold_path}")
    tokenizer, model = load_model(esmfold_path, "cuda:1")
    print(f"ESMFold loaded successfully")
    print(f"Start predicting structure for sequence: {protein_sequence}")
    
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d_%H-%M-%S")
    save_path = f"{tmp_pdb_dir}/{now_str}.pdb"
    os.makedirs(tmp_pdb_dir, exist_ok=True)
    predict(protein_sequence, tokenizer, model, save_path=save_path)
    print(f"Protein structure saved successfully. Saved to {save_path}")
    
    foldseek_str = get_foldseek(save_path, foldseek_path).lower()
    return protein_sequence, foldseek_str

def structure_args(protein_structure, foldseek_path):
    protein_sequence = extract_aa_sequence(protein_structure)
    foldseek_str = get_foldseek(protein_structure, foldseek_path).lower()
    return protein_sequence, foldseek_str

def chat_stream(question, protein_sequence, foldseek_structure, rag_results=""):
    client = Client("http://www.chat-protein.com/")
    job = client.submit(
            question, protein_sequence, foldseek_structure, rag_results,
            api_name="/chat"
    )
    
    async def print_responses():
        filtered_previous_length = 0
        
        async def fetch_updates():
            nonlocal filtered_previous_length
            while not job.done():
                await asyncio.sleep(0.1)
                try:
                    outputs = job.outputs()
                except Exception as e:
                    print(f"Error fetching outputs: {str(e)}")
                    continue
                if outputs is None:
                    print("No outputs available yet")
                    continue
                
                if isinstance(outputs, list) and outputs:
                    latest_output = outputs[-1]
                    filtered_output = re.sub(r'^.*?</span>', '', latest_output, count=1, flags=re.DOTALL)
                    new_content = filtered_output[filtered_previous_length:]
                    if new_content:
                        print(new_content, end="", flush=True)
                        filtered_previous_length = len(filtered_output)

        await fetch_updates()
    
    asyncio.run(print_responses())
    

def get_args():
    parser = argparse.ArgumentParser(description="Protein Chat Caller")
    parser.add_argument("--question", type=str, help="Question to ask the model")
    parser.add_argument("--uniprot_id", type=str, help="Uniprot ID of the protein")
    parser.add_argument("--protein_sequence", type=str, help="Protein sequence")
    parser.add_argument("--protein_structure", type=str, help="Protein structure")
    parser.add_argument("--tmp_pdb_dir", type=str, help="Temporary directory to save PDB files")
    parser.add_argument("--esmfold_path", type=str, help="Path to the ESMFold model")
    parser.add_argument("--foldseek_path", type=str, help="Path to the FoldSeek model")
    return parser.parse_args()

def main(args):
    if args.uniprot_id:
        protein_sequence, foldseek_str = id_args(args.uniprot_id, args.tmp_pdb_dir, args.foldseek_path)
    elif args.protein_sequence:
         protein_sequence, foldseek_str = seq_args(args.protein_sequence, args.tmp_pdb_dir, args.esmfold_path, args.foldseek_path)
    elif args.protein_structure:
        protein_sequence, foldseek_str = structure_args(args.protein_structure, args.foldseek_path)
    else:
        raise ValueError("Invalid input")
    try:
        chat_stream(args.question, protein_sequence, foldseek_str)
    except Exception as e:
        print(e, file=sys.stderr)

if __name__ == "__main__":
    """EXAMPLE:
        python command.py   --question "What is the function of this protein?" \
                        --uniprot_id "P06213" \
                        --tmp_pdb_dir "./tmp" \
                        --foldseek_path "/root/ProtAgent/bin/foldseek" \
                        --esmfold_path "/root/ProtAgent/modelhub/esmfold_v1"
    """
    args = get_args()
    main(args)