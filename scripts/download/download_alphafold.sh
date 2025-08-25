#!/bin/bash -e

type wget 2>/dev/null || { echo "wget is not installed. Please install it using apt or yum." ; exit 1 ; }

COLABFOLDDIR="modelhub/colabfold"
ENV_NAME="colabfold"
mkdir -p "${COLABFOLDDIR}"
cd "${COLABFOLDDIR}"
conda activate $ENV_NAME


# Download weights
python3 -m colabfold.download
echo "Download of alphafold2 weights finished."
echo "-----------------------------------------"
echo "Installation of ColabFold finished."
echo "For more details, please run 'colabfold_batch --help'."