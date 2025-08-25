import shlex
import sys

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
import os
import datetime
import torch
import biotite.structure.io as bsio

from agent.tools.base_tool import BaseTool
from agent.tools.register import register_tool


torch.backends.cuda.matmul.allow_tf32 = True
BASE_DIR = os.path.dirname(__file__)
sys.path.append(BASE_DIR)

@register_tool
class Umol(BaseTool):
    def __init__(self, out_dir: str = f"{ROOT_DIR}/outputs/umol", **kwargs):
        super().__init__(
            config_path=f"{BASE_DIR}/config.yaml",
            out_dir=out_dir,
            **kwargs
        )
    
    def __call__(self, protein_sequence, ligand_sequence, num_recycles=3, protein_pocket="NONE") -> dict:
        id = "umol01"
        now = datetime.datetime.now()
        now = now.strftime("%Y%m%d_%H%M")
        save_path = f"{self.out_dir}/umol/{now}/{id}"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        original_path = os.environ.get('PATH', '')
        os.environ['PATH'] = '/home/public/miniconda3/envs/umol/bin:' + original_path

        pocket_indices = f"{save_path}/{id}_pocket_indices.npy"
    
        # Search Uniclust30 with HHblits to generate an MSA (a few minutes)
        fasta_path = f"{save_path}/examples.fasta"
        self.sequence_to_fasta(fasta_path, protein_sequence, id)
        
        UNICLUST = f"{ROOT_DIR}/{self.config['UNICLUST']}"
        HHBLITS = f"{ROOT_DIR}/{self.config['HHBLITS']}"
        
        try:
            cmd = f"{HHBLITS} -i '{fasta_path}' -d '{UNICLUST}'\
                -E 0.001 -all -oa3m '{save_path}/{id}.a3m' -o '{save_path}/{id}.hhr'"
            os.system(cmd)
            
            # Generate input feats (seconds)
            cmd = f"{self.config['python']} {ROOT_DIR}/agent/tools/umol/umol/make_msa_seq_feats.py \
                                                        --input_fasta_path '{fasta_path}' \
                                                        --input_msas '{save_path}/{id}.a3m' \
                                                        --outdir '{save_path}'"
            os.system(cmd)
            
            # SMILES. Alt: --input_sdf 'path_to_input_sdf'
            cmd = f"{self.config['python']} {ROOT_DIR}/agent/tools/umol/umol/make_ligand_feats.py \
                                                        --input_smiles '{ligand_sequence}' \
                                                        --outdir '{save_path}'"
            os.system(cmd)
            
            if protein_pocket != "NONE":
                cmd = f"{self.config['python']} {ROOT_DIR}/agent/tools/umol/umol/make_targetpost_npy.py \
                                                        --outfile '{pocket_indices}' \
                                                        --target_pos '{protein_pocket}'"
                os.system(cmd)
                
                ckpt = f"{ROOT_DIR}/{self.config['POCKET_PARAMS']}"
                
            else:
                ckpt = f"{ROOT_DIR}/{self.config['NO_POCKET_PARAMS']}"
                pocket_indices = "NONE"
                
            # Predict (a few minutes)
            msa_feats = f"{save_path}/msa_features.pkl"
            ligand_feats = f"{save_path}/ligand_inp_features.pkl"
            
            #Change to no-pocket params if no pocket
            #Then also leave out the target protein_pocket
            
            cmd = f"{self.config['python']} {ROOT_DIR}/agent/tools/umol/umol/predict.py \
                                                        --msa_features '{msa_feats}' \
                                                        --ligand_features '{ligand_feats}' \
                                                        --id {id} \
                                                        --ckpt_params '{ckpt}' \
                                                        --target_pos '{pocket_indices}' \
                                                        --num_recycles {num_recycles} \
                                                        --outdir '{save_path}'"
            os.system(cmd)
            
            
            raw_pdb = f"{save_path}/{id}_pred_raw.pdb"
            cmd = f"{self.config['python']} {ROOT_DIR}/agent/tools/umol/umol/relax/align_ligand_conformer.py \
                                                        --pred_pdb '{raw_pdb}' \
                                                        --ligand_smiles '{ligand_sequence}' \
                                                        --outdir '{save_path}'"
            os.system(cmd)
            
            cmd = f"grep ATOM '{save_path}/{id}_pred_raw.pdb' > '{save_path}/{id}_pred_protein.pdb'"
            os.system(cmd)
            
            
            # Relax the protein (a few minutes)
            # This fixes clashes mainly in the protein, but also in the protein-ligand interface.
            
            pred_protein = f"{save_path}/{id}_pred_protein.pdb"
            pred_ligand = f"{save_path}/{id}_pred_ligand.sdf"
            restraints = "CA+ligand" # or "protein"
            cmd = f"{self.config['python']} {ROOT_DIR}/agent/tools/umol/umol/relax/openmm_relax.py \
                                                        --input_pdb '{pred_protein}' \
                                                        --ligand_sdf '{pred_ligand}' \
                                                        --file_name {id} \
                                                        --restraint_type {restraints} \
                                                        --outdir '{save_path}'"
            os.system(cmd)
            
            #Write plDDT to Bfac column
            raw_complex = f"{save_path}/{id}_pred_raw.pdb"
            relaxed_complex = f"{save_path}/{id}_relaxed_complex.pdb" 
            cmd = f"{self.config['python']} {ROOT_DIR}/agent/tools/umol/umol/relax/add_plddt_to_relaxed.py \
                                                            --raw_complex '{raw_complex}' \
                                                            --relaxed_complex '{relaxed_complex}' \
                                                            --outdir '{save_path}'"
            os.system(cmd)
            
            if os.path.exists(f"{save_path}/{id}_relaxed_plddt.pdb"):
                struct = bsio.load_structure(f"{save_path}/{id}_relaxed_plddt.pdb", extra_fields=["b_factor"])
                avg_plddt = float(struct.b_factor.mean())
                print(f"The final relaxed structure can be found at {save_path[len(self.out_dir)+1:]}/{id}_relaxed_plddt.pdb")
                return {"complex_structure": f"{save_path[len(self.out_dir)+1:]}/{id}_relaxed_plddt.pdb", "avg_plddt": avg_plddt}
            else:
                return {"error": "Failed to run umol"}
        except Exception as e:
            return {"error": str(e)}

    def sequence_to_fasta(self, file_path, sequence, id):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(file_path, "w") as fasta_file:
            fasta_file.write(f">{id}\n")
            sequence = sequence.replace(" ", "").replace("\n", "")
            fasta_file.write(f"{sequence}\n")


if __name__ == '__main__':
    # Test
    umol = Umol(BASE_DIR)
    
    input_args = {
        "protein_sequence": "GSHSMRYFYTAMSRPGRGEPRFIAVGYVDDTQFVRFDSDAASPRMAPRAPWIEQEGPEYWDRETQISKTNTQTYRESLRNLRGYYNQSEAGSHTLQRMYGCDVGPDGRLLRGHDQSAYDGKDYIALNEDLSSWTAADTAAQITQRKWEAAREAEQWRAYLEGLC VEWLRRYLENG",
        "ligand_sequence": "CCc1sc2ncnc(N[C@H](Cc3ccccc3)C(=O)O)c2c1-c1cccc(Cl)c1C",
        "num_recycles": 3,
        "protein_pocket": "NONE"
        }
    obs = umol.run(**input_args)
    print(obs)

    