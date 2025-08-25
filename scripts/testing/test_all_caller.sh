#!/bin/bash

# Set the path to traverse
base_path="funchub/func_doc"

# Folders to ignore
ignore_folders=("structure_prediction" "protein_design")

# Loop through each folder in the path
for folder in "$base_path"/*; do
  if [ -d "$folder" ]; then
    # Get the folder name
    folder_name=$(basename "$folder")
        
    echo "##################################################" >> scripts/testing/test_all_caller.log 2>&1
    echo "Testing ${folder_name}" >> scripts/testing/test_all_caller.log 2>&1
    echo "Testing ${folder_name}"
    echo "##################################################" >> scripts/testing/test_all_caller.log 2>&1

    # Check if the folder is in the ignore list
    if [[ " ${ignore_folders[@]} " =~ " ${folder_name} " ]]; then
      continue  # Skip this folder
    fi
    
    if [ -d "examples/inputs/${folder_name}" ]; then
      echo "Using example inputs in examples/inputs/${folder_name}" >> scripts/testing/test_all_caller.log 2>&1
      # Test in /home/public folder
      python scripts/testing/test_caller.py --caller_tested "${folder_name}" --public --once >> scripts/testing/test_all_caller.log 2>&1
      # Test in ProtAgent folder
      python scripts/testing/test_caller.py --caller_tested "${folder_name}" --once >> scripts/testing/test_all_caller.log 2>&1
    else
      echo "Using GPT generated inputs" >> scripts/testing/test_all_caller.log 2>&1
      # Test in /home/public folder
      python scripts/testing/test_caller.py --caller_tested "${folder_name}" --public --once --use_GPT >> scripts/testing/test_all_caller.log 2>&1
      # Test in ProtAgent folder
      python scripts/testing/test_caller.py --caller_tested "${folder_name}" --once --use_GPT >> scripts/testing/test_all_caller.log 2>&1
    fi
  fi
done
