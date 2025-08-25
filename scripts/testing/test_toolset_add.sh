# Check if the current working directory ends with "ProtAgent"
current_dir=$(basename "$PWD")
if [[ "$current_dir" != "ProtAgent" ]]; then
    echo "Error: Current directory is not 'ProtAgent'. Exiting..."
    exit 1
fi

conda activate agent
python scripts/toolset/add_new_tool.py