#!/bin/bash
eval "$(conda shell.bash hook)"
env_name="colabfold"
conda activate $env_name

for arg in "$@"
do
    case $arg in
        input=*) input="${arg#*=}" ;;
        output_dir=*) output_dir="${arg#*=}" ;;
        msa_mode=*) msa_mode="${arg#*=}" ;;
        *) ;;
    esac
done

# basic colabfold demand
colabfold_command="colabfold_batch $input $output_dir --msa-only"
echo "-------"
echo $colabfold_command

# msa_mode
if [[ "$msa_mode" == "mmseqs2_uniref_env" ]]; then
    # default, no extra paras
    echo "Using MSA mode: mmseqs2_uniref_env"
elif [[ "$msa_mode" == "mmseqs2_uniref" ]]; then
    colabfold_command="$colabfold_command --msa-mode mmseqs2_uniref"
    echo "Using MSA mode: mmseqs2_uniref"
fi

# print final command
echo "Executing: $colabfold_command"
$colabfold_command

# conda deactivate
conda activate agent
