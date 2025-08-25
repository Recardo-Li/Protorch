#!/bin/bash

# Use case: tmalign.sh <TMALIGN_PATH> <ALN_PDB_PATH> <REF_PDB_PATH> <RESULT_PATH>
# Please make sure you are at the project root (e.g., ProtAgent).

# Check parameter usage
if [ "$#" -ne 4 ]; then
    echo "Usage: tmalign.sh <TMALIGN_PATH> <ALN_PDB_PATH> <REF_PDB_PATH> <RESULT_PATH>"
    exit 1
fi

echo "Running TMAlign to align $2 against $3 and save results to $4"

# Check directory
current_path=$(pwd)
echo "current_path=$current_path"
if [ $(basename "$current_path") != "ProtAgent" ]; then
    echo "Please make sure you are at the project root (e.g., ProtAgent)"
    exit 1
fi

# Assign input arguments to variables
TMALIGN_PATH=$1
ALN_PDB_PATH=$2
REF_PDB_PATH=$3
RESULT_PATH=$4

# Run TMAlign
$TMALIGN_PATH $ALN_PDB_PATH $REF_PDB_PATH > $RESULT_PATH

# Check for errors
if [ $? -ne 0 ]; then
    echo "TMAlign execution failed. Please check your inputs and the TMAlign binary."
    exit 1
else
    echo "TMAlign execution completed successfully. Results saved to $RESULT_PATH"
fi
