import os
import sys
import argparse
ROOT_DIR = __file__.rsplit("/", 5)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
# PATH = os.environ.get("PATH")
# new_path = "/opt/conda/envs/antibody/bin"
# if new_path not in PATH:
#     print("################ Add /opt/conda/envs/antibody/bin to PATH ##############")
#     os.environ["PATH"] = PATH + os.pathsep + new_path
    
from agent.tools.diffab.diffab.tools.runner.design_for_pdb import design_for_pdb
from agent.tools.diffab.diffab.evaluation import eval_pipeline

def args_from_cmdline():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdb_path', type=str, default="dataset/diffab/7DK2_AB_C.pdb")
    parser.add_argument('--heavy', type=str, default="H", help='Chain id of the heavy chain.')
    parser.add_argument('--light', type=str, default="L", help='Chain id of the light chain.')
    parser.add_argument('--antigen', default=None, help='Chain id of the antigen')
    parser.add_argument('--renumber', default=True)
    parser.add_argument('--num_samples', type=int, default=10)
    parser.add_argument('-c', '--config', type=str, default='model/diffab/configs/test/strpred.yml')
    parser.add_argument('-o', '--out_root', type=str, default='outputs/diffab_antigen_antibody')
    parser.add_argument('--model_dir', type=str, default='')
    parser.add_argument('-t', '--tag', type=str, default='')
    parser.add_argument('-s', '--seed', type=int, default=None)
    parser.add_argument('-d', '--device', type=str, default='cuda')
    parser.add_argument('-b', '--batch_size', type=int, default=32)
    parser.add_argument('--relax_distance', type=int, default=6)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = args_from_cmdline()
    design_for_pdb(args)
    eval_pipeline(pdb_dir=args.out_root,
                  chain_h=args.heavy,
                  chain_l=args.light,
                  chain_a=args.antigen,
                  relax_distance=args.relax_distance,
                  repeats=args.repeats)