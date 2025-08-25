#!/bin/bash
eval "$(conda shell.bash hook)"

conda activate SE3nv

for arg in "$@"
do
    case $arg in
        output_path=*) output_path="${arg#*=}" ;;
        iterations=*) iterations="${arg#*=}" ;;
        symmetry=*) symmetry="${arg#*=}" ;;
        order=*) order="${arg#*=}" ;;
        hotspot=*) hotspot="${arg#*=}" ;;
        chains=*) chains="${arg#*=}" ;;
        add_potential=*) add_potential="${arg#*=}" ;;
        partial_T=*) partial_T="${arg#*=}" ;;
        num_designs=*) num_designs="${arg#*=}" ;;
        use_beta_model=*) use_beta_model="${arg#*=}" ;;
        visual=*) visual="${arg#*=}" ;;
        contigs=*) contigs="${arg#*=}" ;;
        pdb=*) pdb="${arg#*=}" ;;
        *) ;;
    esac
done

python funchub/func_impl/rf_diffusion/test_rf_runner.py \
    --output_path "$output_path" \
    --iterations "$iterations" \
    --symmetry "$symmetry" \
    --order "$order" \
    --hotspot "$hotspot" \
    --chains "$chains" \
    --add_potential "$add_potential" \
    --partial_T "$partial_T" \
    --num_designs "$num_designs" \
    --use_beta_model "$use_beta_model" \
    --visual "$visual" \
    --contigs "$contigs" \
    --pdb "$pdb"


conda activate agent
