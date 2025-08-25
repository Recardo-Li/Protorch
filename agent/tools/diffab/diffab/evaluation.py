# pyright: reportMissingImports=false, reportRedeclaration=false
import pyrosetta

from pyrosetta.rosetta.protocols.analysis import InterfaceAnalyzerMover
from pyrosetta.rosetta.protocols.relax import FastRelax
from pyrosetta.rosetta.core.select.residue_selector import InterGroupInterfaceByVectorSelector, OrResidueSelector, ChainSelector
from pyrosetta.rosetta.core.select import get_residues_from_subset

import argparse
from pathlib import Path
from Bio.PDB import PDBParser
import json

# init PyRosetta
pyrosetta.init(
    '-beta_nov16 -ex1 -ex2 -use_input_sc '
    '-mute all '
    '-ignore_unrecognized_res'
)

def find_numeric_pdb_filepaths_pathlib(directory_path):
    root_path = Path(directory_path)
    if not root_path.is_dir():
        print(f"Error: '{root_path}' not exist!")
        return []

    pdb_filepaths = []
    
    for file_path in root_path.rglob('*.pdb'):
        if file_path.stem.isdigit():
            pdb_filepaths.append(str(file_path))
            
    return pdb_filepaths

def get_antigen_id(pdb_file, chain_h="H", chain_l="L"):
    parser = PDBParser()
    structure = parser.get_structure("protein", pdb_file)
    
    chain_ids = []
    for model in structure:
        for chain in model:
            chain_ids.append(chain.id)
    chain_as = list(set(chain_ids) - set([chain_h, chain_l]))
    if chain_as:
        return chain_as[0]
    else:
        return None


def relax_antibody_interface(pose, heavy_chain, light_chain, antigen_chain=None, relax_distance=8, repeats=5):
    print(f"--- Starting specific relaxation of the interface (distance threshold: {relax_distance} Å, cycles: {repeats}) ---")
    movemap = pyrosetta.MoveMap()
    movemap.set_bb(False); movemap.set_chi(False)

    # ========================== CHANGE START ==========================
    
    # 1. VH-VL interface selecter
    vh_vl_sel = InterGroupInterfaceByVectorSelector()
    vh_vl_sel.group1_selector(ChainSelector(heavy_chain))
    vh_vl_sel.group2_selector(ChainSelector(light_chain))
    vh_vl_sel.nearby_atom_cut(relax_distance)
    
    final_selector = vh_vl_sel

    if antigen_chain:
        # 2. antigen-antibody interface selecter
        ab_ag_sel = InterGroupInterfaceByVectorSelector()
        ab_ag_sel.group1_selector(ChainSelector(f"{heavy_chain},{light_chain}"))
        ab_ag_sel.group2_selector(ChainSelector(antigen_chain))
        ab_ag_sel.nearby_atom_cut(relax_distance)
        
        # 3. combine
        final_selector = OrResidueSelector(vh_vl_sel, ab_ag_sel)
    # =========================== CHANGE END ===========================

    interface_residues = get_residues_from_subset(final_selector.apply(pose))
    print(f"Identified {len(interface_residues)} interface residues for full relaxation.")
    for res_idx in interface_residues:
        movemap.set_bb(res_idx, True)
        movemap.set_chi(res_idx, True)
        
    scorefxn = pyrosetta.create_score_function('ref2015_cart')
    relax_mover = FastRelax(scorefxn, repeats)
    relax_mover.set_movemap(movemap)
    relax_mover.cartesian(True)

    relaxed_pose = pose.clone()
    relax_mover.apply(relaxed_pose)
    print("--- Interface relaxation completed ---")
    return relaxed_pose

def calculate_interface_scores(pose, interface_definition):
    """
    Calculate the binding energy (dG_separated) of the interface for the given Pose object.
    """
    interface_mover = InterfaceAnalyzerMover(interface_definition)
    interface_mover.set_pack_separated(True)
    interface_mover.apply(pose)
    
    scores = {
        'dG_separated': pose.scores.get('dG_separated', 'N/A'),
        'dSASA_int': pose.scores.get('dSASA_int', 'N/A'), # Buried Solvent Accessible Surface Area
        'sc_value': pose.scores.get('sc_value', 'N/A')    # Shape Complementarity
    }
    return scores


def eval_pipeline(pdb_dir, chain_h="H", chain_l="L", chain_a=None, relax_distance=8, repeats=5):
    top_n = 1
    all_pdb_files = find_numeric_pdb_filepaths_pathlib(pdb_dir)
    if not all_pdb_files:
        print(f"Error: No .pdb files found in directory '{pdb_dir}'.")
        exit()

    print(f"Found {len(all_pdb_files)} PDB file(s). Starting filtering process...\n")

    # get antibody chain id
    if not chain_a:
        chain_a = get_antigen_id(all_pdb_files[0], chain_h=chain_h, chain_l=chain_l)
    
    ab_ag_interface_def = f"{chain_h}{chain_l}_{chain_a}"
    
    print("================== STAGE 1: Geometric Scoring & Ranking =============")
    stage1_all_scores = []
    all_pdb_files = dict(enumerate(all_pdb_files))

    # Performing initial structure screening based on geometric criteria
    for index, pdb_path in all_pdb_files.items():
        print(f"Processing pdb{index}...")
        try:
            pose = pyrosetta.pose_from_pdb(pdb_path)
            scores = calculate_interface_scores(pose, ab_ag_interface_def)
            sasa = scores.get('dSASA_int', 0.0)
            sc = scores.get('sc_value', 0.0)
            
            combined_score = sasa * sc
            
            print(f"  dSASA={sasa:.1f}, sc={sc:.3f}, Combined_Score={combined_score:.1f}")
            stage1_all_scores.append({
                'index': index,
                'path': pdb_path, 
                'pose': pose, 
                'sasa': sasa, 
                'sc': sc,
                'combined_score': combined_score
            })
        except Exception as e:
            print(f"  [ERROR] Loading or processing pdb{index} failed: {e}")


    stage1_all_scores.sort(key=lambda x: x['combined_score'], reverse=True)
    
    stage1_results = stage1_all_scores[:top_n]
    
    print(f"\nStage 1 Summary: Selected top {len(stage1_results)} candidate(s) based on combined geometric score.")
    print("Top candidates passing Stage 1:")
    for cand in stage1_results:
        print(f"  - pdb{cand['index']} (Score: {cand['combined_score']:.1f})")

    print("================== STAGE 2: Full Relaxation & Final Analysis =======")
    final_results = []
    for candidate in stage1_results:
        print(f"Processing pdb{candidate['index']}...")
        try:
            # relax the strcuture generated by diffab
            relaxed_pose = relax_antibody_interface(candidate['pose'], chain_h, chain_l, chain_a, relax_distance=relax_distance, repeats=repeats)
            
            final_ab_ag_scores = calculate_interface_scores(relaxed_pose, ab_ag_interface_def)
            candidate['final_scores_ab_ag'] = final_ab_ag_scores
            final_results.append(candidate)
            
            # save the relaxed structure
            relaxed_pose.dump_pdb(f"{pdb_dir}/final_relaxed.pdb")

        except Exception as e:
            print(f"  [ERROR] Stage 2 processing for pdb{candidate['index']} failed: {e}")
    
    # rank the final strcture based on dG_separated
    final_results.sort(key=lambda x: x['final_scores_ab_ag']['dG_separated'])
    
    # save the final score
    with open(f"{pdb_dir}/final_score.json", "w+") as f:
        json.dump(final_ab_ag_scores, f, indent=4)
    
    # --- output final results ---
    print("\n\n========================= FINAL RANKED RESULTS =========================")
    for i, result in enumerate(final_results):
        print(f"\n----------- Rank {i+1}: {result['index']} -----------")
        print("  Antibody-Antigen Interface:")
        ab_ag = result['final_scores_ab_ag']
        print(f"    - Binding Energy (dG): {ab_ag['dG_separated']:.2f} REU")
        print(f"    - Buried SASA (dSASA): {ab_ag['dSASA_int']:.1f} Å²")
        print(f"    - Shape Complementarity (sc): {ab_ag['sc_value']:.3f}")

    print("\n========================================================================")

def args_from_cmdline():
    parser = argparse.ArgumentParser()
    parser.add_argument('--heavy', type=str, default="H", help='Chain id of the heavy chain.')
    parser.add_argument('--light', type=str, default="L", help='Chain id of the light chain.')
    parser.add_argument('--antigen', default=None, help='Chain id of the antigen')
    parser.add_argument('--out_root', type=str, default='outputs/diffab_antigen_antibody')
    parser.add_argument('--relax_distance', type=int, default=6)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = args_from_cmdline()
    # INPUT_PDB_DIR = "example/diffab_design/20250730_0855"

    args = {
        "pdb_dir": args.out_root,
        "chain_h": args.heavy, 
        "chain_l": args.light,
        "chain_a": args.antigen,  
        "relax_distance": args.relax_distance, 
        "repeats": args.repeats
        }
    
    eval_pipeline(**args)
    