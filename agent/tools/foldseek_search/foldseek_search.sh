#!/bin/bash

# Use case: foldseek_search.sh <FOLDSEEK_PATH> <QUERY_PDB_PATH> <DATABASE_PATH> <RESULT_PATH> [MAX_RESULTS] [EVALUE_THRESHOLD]
# Please make sure you are at the project root (e.g., ProtAgent).

# Check parameter usage
if [ "$#" -lt 4 ]; then
    echo "Usage: foldseek_search.sh <FOLDSEEK_PATH> <QUERY_PDB_PATH> <DATABASE_PATH> <RESULT_PATH> [MAX_RESULTS] [EVALUE_THRESHOLD]"
    echo "  FOLDSEEK_PATH: Path to foldseek binary"
    echo "  QUERY_PDB_PATH: Path to query PDB file"
    echo "  DATABASE_PATH: Path to foldseek database (e.g., PDB, AlphaFold)"
    echo "  RESULT_PATH: Path to save search results"
    echo "  MAX_RESULTS: Maximum number of results to return (default: 100)"
    echo "  EVALUE_THRESHOLD: E-value threshold for filtering results (default: 1e-3)"
    exit 1
fi

echo "Running Foldseek search on $2 against database $3 and saving results to $4"

# Check directory
current_path=$(pwd)
echo "current_path=$current_path"
if [ $(basename "$current_path") != "ProtAgent" ]; then
    echo "Please make sure you are at the project root (e.g., ProtAgent)"
    exit 1
fi

# Assign input arguments to variables
FOLDSEEK_PATH=$1
QUERY_PDB_PATH=$2
DATABASE_PATH=$3
RESULT_PATH=$4
MAX_RESULTS=${5:-100}
EVALUE_THRESHOLD=${6:-1e-3}

# Create temporary directory for intermediate files
TEMP_DIR=$(mktemp -d)
TEMP_QUERY_DB="$TEMP_DIR/query_db"
TEMP_RESULT="$TEMP_DIR/result"

echo "Creating temporary query database..."

# Create database from query structure
$FOLDSEEK_PATH createdb $QUERY_PDB_PATH $TEMP_QUERY_DB --threads 1

if [ $? -ne 0 ]; then
    echo "Failed to create query database"
    rm -rf $TEMP_DIR
    exit 1
fi

echo "Searching for similar structures..."

# Perform structure search
$FOLDSEEK_PATH search $TEMP_QUERY_DB $DATABASE_PATH $TEMP_RESULT $TEMP_DIR \
    --max-seqs $MAX_RESULTS \
    -e $EVALUE_THRESHOLD \
    --threads 1 \
    -v 1

if [ $? -ne 0 ]; then
    echo "Foldseek search failed. Please check your inputs and the database."
    rm -rf $TEMP_DIR
    exit 1
fi

echo "Converting results to readable format..."

# Convert results to readable format
$FOLDSEEK_PATH convertalis $TEMP_QUERY_DB $DATABASE_PATH $TEMP_RESULT $RESULT_PATH \
    --format-output "query,target,pident,alnlen,mismatch,gapopen,qstart,qend,tstart,tend,evalue,bits" \
    --threads 1

# Check for errors
if [ $? -ne 0 ]; then
    echo "Failed to convert results to readable format"
    rm -rf $TEMP_DIR
    exit 1
fi

# Clean up temporary files
rm -rf $TEMP_DIR

echo "Foldseek search completed successfully. Results saved to $RESULT_PATH"
echo "Found similar structures with E-value <= $EVALUE_THRESHOLD" 