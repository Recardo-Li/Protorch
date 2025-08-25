#!/bin/bash

# input json dir
INPUT_DIR="outputs/large_data/json_results_key_filtered"
# python script path
PYTHON_SCRIPT="scripts/testing/test_retriever.py"

# traverse all json files from input json dir
for json_file in "$INPUT_DIR"/*.json; do
    
    if [[ -f "$json_file" ]]; then
        echo "Processing file: $json_file"
        # run py scripts, and pass parameters "input"
        python "$PYTHON_SCRIPT" --input "$json_file"
    else
        echo "No JSON files found in directory: $INPUT_DIR"
    fi
done