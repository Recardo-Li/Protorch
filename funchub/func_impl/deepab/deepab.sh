#!/bin/bash

eval "$(conda shell.bash hook)"
fasta_file="examples/fasta/deepab/4h0h.fasta"
pred_dir="outputs/deepab"
decoys=5
renumber=true
single_chain=false
env_name="antibody"

for arg in "$@"
do
    case $arg in
        fasta_file=*) fasta_file="${arg#*=}" ;;
        pred_dir=*) pred_dir="${arg#*=}" ;;
        decoys=*) decoys="${arg#*=}" ;;
        renumber=*) renumber="${arg#*=}" ;;
        single_chain=*) single_chain="${arg#*=}" ;;
        env_name=*) env_name="${arg#*=}" ;;
        *) ;;
    esac
done

conda activate $env_name
python model/deepab/deepab.py --fasta_file $fasta_file \
                              --pred_dir $pred_dir \
                              --decoys $decoys \
                              --renumber $renumber \
                              --single_chain $single_chain

conda deactivate
