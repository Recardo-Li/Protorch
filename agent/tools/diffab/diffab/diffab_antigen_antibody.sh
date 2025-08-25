#!/bin/bash

eval "$(conda shell.bash hook)"
pdb_path="examples/pdb/diffab/7DK2_AB_C.pdb"
out_root="outputs/diffab_antigen_antibody"
config="model/diffab/configs/test/strpred.yml"
num_samples=10
model_dir="huggingface/DiffAb/DiffAb/codesign_multicdrs.pt"
relax_distance=6
repeats=3


env_name="antibody"

for arg in "$@"
do
    case $arg in
        root_dir=*) root_dir="${arg#*=}" ;;
        pdb_path=*) pdb_path="${arg#*=}" ;;
        out_root=*) out_root="${arg#*=}" ;;
        config=*) config="${arg#*=}" ;;
        num_samples=*) num_samples="${arg#*=}" ;;
        model_dir=*) model_dir="${arg#*=}" ;;
        relax_distance=*) relax_distance="${arg#*=}" ;;
        repeats=*) repeats="${arg#*=}" ;;
        env_name=*) env_name="${arg#*=}" ;;
        *) ;;
    esac
done

conda activate $env_name
python ${root_dir}/agent/tools/diffab/diffab/diffab_antigen_antibody.py --pdb_path $pdb_path \
                                               --out_root $out_root \
                                               --config $config \
                                               --num_samples $num_samples \
                                               --relax_distance $relax_distance \
                                               --repeats $repeats \
                                               --model_dir $model_dir

conda deactivate
