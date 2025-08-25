#!/bin/bash

eval "$(conda shell.bash hook)"
antigen="examples/pdb/diffab/7DK2_AB_C.pdb"
antibody="examples/pdb/diffab/3QHF_Fv.pdb"
out_root="outputs/diffab_antigen_only"
tmp_root="tmp/diffab_antigen_only"
config="model/diffab/configs/test/strpred.yml"
hdock_bin='bin/diffab/hdock'
createpl_bin='bin/diffab/createpl'
decoys=10
num_samples=10
model_dir="huggingface/DiffAb/DiffAb/codesign_multicdrs.pt"

env_name="antibody"

for arg in "$@"
do
    case $arg in
        root_dir=*) root_dir="${arg#*=}" ;;
        antigen=*) antigen="${arg#*=}" ;;
        antibody=*) antibody="${arg#*=}" ;;
        out_root=*) out_root="${arg#*=}" ;;
        tmp_root=*) tmp_root="${arg#*=}" ;;
        hdock_bin=*) hdock_bin="${arg#*=}" ;;
        createpl_bin=*) createpl_bin="${arg#*=}" ;;
        config=*) config="${arg#*=}" ;;
        decoys=*) decoys="${arg#*=}" ;;
        num_samples=*) num_samples="${arg#*=}" ;;
        model_dir=*) model_dir="${arg#*=}" ;;
        relax_distance=*) relax_distance="${arg#*=}" ;;
        repeats=*) repeats="${arg#*=}" ;;
        env_name=*) env_name="${arg#*=}" ;;
        *) ;;
    esac
done

conda activate $env_name
python ${root_dir}/agent/tools/diffab/diffab/diffab_antigen_only.py --antigen $antigen \
                                           --antibody $antibody \
                                           --out_root $out_root \
                                           --tmp_root $tmp_root \
                                           --config $config \
                                           --hdock_bin $hdock_bin \
                                           --createpl_bin $createpl_bin \
                                           --decoys $decoys \
                                           --num_samples $num_samples \
                                           --relax_distance $relax_distance \
                                           --repeats $repeats \
                                           --model_dir $model_dir

conda deactivate
