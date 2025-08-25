#!/bin/bash
eval "$(conda shell.bash hook)"
env_name="interproscan"
conda activate $env_name

for arg in "$@"
do
    case $arg in
        interproscan_cmd=*) interproscan_cmd="${arg#*=}" ;;
        *) ;;
    esac
done

# echo $interproscan_cmd
$interproscan_cmd
