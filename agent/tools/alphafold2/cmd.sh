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
        template_mode=*) template_mode="${arg#*=}" ;;
        template_path=*) template_path="${arg#*=}" ;;

        *) ;;
    esac
done

# basic colabfold demand
colabfold_command="colabfold_batch $input $output_dir"
echo "-------"
echo $colabfold_command

# msa_mode
if [[ "$msa_mode" == "mmseqs2_uniref_env" ]]; then
    # default, no extra paras
    echo "Using MSA mode: mmseqs2_uniref_env"
elif [[ "$msa_mode" == "single_sequence" ]]; then
    colabfold_command="$colabfold_command --msa-mode single_sequence"
    echo "Using MSA mode: single_sequence"
fi

# template_mode
if [[ "$template_mode" == "pdb100" ]]; then
    colabfold_command="$colabfold_command --templates"
    echo "Using template mode: pdb100"
elif [[ "$template_mode" == "custom" ]]; then
    if [[ -n "$template_path" ]]; then
        # -n to test whether template_path is provided or not
        colabfold_command="$colabfold_command --templates --custom-template-path $template_path"
        echo "Using template mode: custom with path $template_path"
    else
        echo "Error: template_path is required when template_mode is set to 'custom'."
        exit 1
    fi
fi

# print final command
echo "Executing: $colabfold_command"
$colabfold_command

# conda deactivate
conda activate agent
