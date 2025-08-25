#!/bin/bash

# Use case: foldseek.sh <FOLDSEEK_PATH> <PDB_PATH> <RESULT_PATH>
# Please make sure you are at the project root (e.g., ProtAgent).

# Check parameter usage
if [ "$#" -ne 3 ]; then
    echo "Usage: foldseek.sh <FOLDSEEK_PATH> <PDB_PATH> <RESULT_PATH>"
    exit 1
fi

echo "Running Foldseek on $2 and saving results to $3"

# Check directory
current_path=$(pwd)
echo "current_path=$current_path"
if [ $(basename "$current_path") != "ProtAgent" ]; then
    echo "Please make sure you are at the project root (e.g., ProtAgent)"
    exit 1
fi

# Assign input arguments to variables
FOLDSEEK_PATH=$1
PDB_PATH=$2
RESULT_PATH=$3

# Run Foldseek with specified options
$FOLDSEEK_PATH structureto3didescriptor -v 0 --threads 1 --chain-name-mode 1 $PDB_PATH $RESULT_PATH

# Check for errors
if [ $? -ne 0 ]; then
    echo "Foldseek execution failed. Please check your inputs and the Foldseek binary."
    exit 1
else
    echo "Foldseek execution completed successfully. Results saved to $RESULT_PATH"
fi
