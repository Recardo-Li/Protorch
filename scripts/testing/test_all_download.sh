#!/bin/bash

base_path="scripts/download"

# Check if the current working directory ends with "ProtAgent"
current_dir=$(basename "$PWD")
if [[ "$current_dir" != "ProtAgent" ]]; then
    echo "Error: Current directory is not 'ProtAgent'. Exiting..."
    exit 1
fi

for script in "$base_path"/*; do
    # Run the script
    bash "$script"

    # Check again if the current working directory ends with "ProtAgent"
    current_dir_after=$(basename "$PWD")
    if [[ "$current_dir_after" != "ProtAgent" ]]; then
        echo "Error: Current directory is not 'ProtAgent'. Exiting..."
        exit 1
    fi
done
