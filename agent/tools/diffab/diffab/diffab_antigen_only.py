import os
import sys
import shutil
import argparse
from easydict import EasyDict

ROOT_DIR = __file__.rsplit("/", 5)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)


from agent.tools.diffab.diffab.tools.dock.hdock import HDockAntibody
from agent.tools.diffab.diffab.tools.runner.design_for_pdb import design_for_pdb
from agent.tools.diffab.diffab.evaluation import eval_pipeline

def args_factory(**kwargs):
    default_args = EasyDict(
        heavy = 'H',
        light = 'L',
        renumber = True,
        config = 'model/diffab/configs/test/codesign_single.yml',
        out_root = 'outputs/diffab',
        tag = '',
        seed = None,
        device = 'cuda',
        batch_size = 16
    )
    default_args.update(kwargs)
    return default_args

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--antigen', type=str, required=False, default="dataset/diffab/7DK2_AB_C.pdb")
    parser.add_argument('--antibody', type=str, default='dataset/diffab/3QHF_Fv.pdb')
    parser.add_argument('--heavy', type=str, default='H', help='Chain id of the heavy chain.')
    parser.add_argument('--light', type=str, default='L', help='Chain id of the light chain.')
    parser.add_argument('--renumber', default=True)
    parser.add_argument('--hdock_bin', type=str, default='bin/diffab/hdock')
    parser.add_argument('--createpl_bin', type=str, default='bin/diffab/createpl')
    parser.add_argument('--config', type=str, default='model/diffab/configs/test/codesign_multicdrs.yml')
    parser.add_argument('--out_root', type=str, default='outputs/diffab_antigen_only')
    parser.add_argument('--tmp_root', type=str, default='tmp/diffab_antigen_only')
    parser.add_argument('--model_dir', type=str, default='')
    parser.add_argument('--decoys', type=int, default=10)
    parser.add_argument('--num_samples', type=int, default=10)
    parser.add_argument('--tag', type=str, default='')
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--device', type=str, default='cuda')
    parser.add_argument('--relax_distance', type=int, default=6)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--batch_size', type=int, default=32)
    args = parser.parse_args()

    hdock_missing = []
    if not os.path.exists(args.hdock_bin):
        hdock_missing.append(args.hdock_bin)
    if not os.path.exists(args.createpl_bin):
        hdock_missing.append(args.createpl_bin)
    if len(hdock_missing) > 0:
        print("[WARNING] The following HDOCK applications are missing:")
        for f in hdock_missing:
            print(f" > {f}")
        print("Please download HDOCK from http://huanglab.phys.hust.edu.cn/software/hdocklite/ "
                "and put `hdock` and `createpl` to the above path.")
        exit()
    antigen_name = os.path.basename(os.path.splitext(args.antigen)[0])
    docked_pdb_dir = os.path.join(args.tmp_root, antigen_name+'_dock')
    os.makedirs(docked_pdb_dir, exist_ok=True)
    docked_pdb_paths = []
    with HDockAntibody(hdock_bin=args.hdock_bin, createpl_bin=args.createpl_bin, tmpdir=args.tmp_root) as dock_session:
        dock_session.set_antigen(args.antigen)
        dock_session.set_antibody(args.antibody)
        docked_tmp_paths = dock_session.dock()
        for i, tmp_path in enumerate(docked_tmp_paths):
            dest_path = os.path.join(docked_pdb_dir, f"{antigen_name}_Ab_{i:04d}.pdb")
            shutil.copyfile(tmp_path, dest_path)
            print(f'[INFO] Copy {tmp_path} -> {dest_path}')
            docked_pdb_paths.append(dest_path)

    for i, pdb_path in enumerate(docked_pdb_paths):
        if i == args.decoys:
            break
        current_args = vars(args)
        current_args['tag'] = antigen_name + f"_{i}"
        design_args = args_factory(
            pdb_path = pdb_path,
            **current_args,
        )
        design_for_pdb(design_args)

    eval_pipeline(pdb_dir=args.out_root,
                  chain_h=args.heavy,
                  chain_l=args.light,
                  relax_distance=args.relax_distance,
                  repeats=args.repeats)

if __name__ == '__main__':
    main()
