#!/bin/bash

# use case: mmseqs_search.sh <MMSEQS_PATH> <QUERY_FASTA_PATH> <TARGET_FASTA_PATH> <OUTPUT_FASTA_PATH> [identity]
# please make sure you are at project root (i.e. ProtAgent)

# check parameter usage
if [ "$#" -lt 4 ] || [ "$#" -gt 5 ]; then
    echo "Usage: mmseqs_search.sh <MMSEQS_PATH> <QUERY_FASTA_PATH> <TARGET_FASTA_PATH> <OUTPUT_FASTA_PATH> [identity]"
    exit 1
fi

make_absolute_path() {
  local path=$1
  if [[ $path = /* ]]; then
    echo "$path"
  else
    echo "$(realpath "../../../$path")"
  fi
}

WORKING_PATH=$(pwd)/outputs/mmseqs_search_tmp

# save DB files in DB dir
DB_DIR=$WORKING_PATH/database
TMP_DIR=$WORKING_PATH/tmp
identity=${5:-0.5}

echo "Running MMseqs to search sequences between $2 (query) and $3 (target), with identity threshold $identity"
echo "Filtered result will be saved to $4"

# check dir
current_path=$(pwd)
echo "current_path=$current_path"
if [ $(basename $current_path) != "ProtAgent" ]; then
    echo "Please make sure you are at project root (i.e. ProtAgent)"
    exit 1
fi

# Clean up existing directories
if [ -d $DB_DIR ]; then
    echo "Removing existing DB_DIR: $DB_DIR"
    rm -rf $DB_DIR
fi

if [ -d $TMP_DIR ]; then
    echo "Removing existing TMP_DIR: $TMP_DIR"
    rm -rf $TMP_DIR
fi

mkdir -p $DB_DIR
mkdir -p $TMP_DIR

cd $DB_DIR

MMSEQS=$(make_absolute_path "$1")
QUERY_FASTA_PATH=$(make_absolute_path "$2")
TARGET_FASTA_PATH=$(make_absolute_path "$3")
OUTPUT_FASTA_PATH=$(make_absolute_path "$4")

# create databases
echo "Creating query database..."
$MMSEQS createdb $QUERY_FASTA_PATH query_db

echo "Creating target database..."
$MMSEQS createdb $TARGET_FASTA_PATH target_db

# search similar sequences
echo "Searching for similar sequences..."
$MMSEQS search query_db target_db result_db $TMP_DIR --min-seq-id $identity

# convert results to tsv format to get matched sequence IDs
echo "Converting search results..."
$MMSEQS convertalis query_db target_db result_db result.tsv

# extract IDs of target sequences that matched query sequences
echo "Extracting matched sequence IDs..."
if [ -f result.tsv ]; then
    cut -f2 result.tsv | sort | uniq > matched_ids.txt
else
    touch matched_ids.txt
fi

# Copy matched_ids.txt to the output directory for caller to use
cp matched_ids.txt "$OUTPUT_FASTA_PATH.matched_ids"

# Clean up temporary directories
cd $(dirname $DB_DIR)
rm -rf $DB_DIR
rm -rf $TMP_DIR

echo "MMseqs search and filtering completed successfully!"