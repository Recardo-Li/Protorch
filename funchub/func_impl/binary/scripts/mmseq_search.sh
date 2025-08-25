#!/bin/bash

# use case: mmseqs_search.sh <QUERY_FASTA_PATH> <TARGET_FASTA_PATH> <ALIGN_FASTA_PATH> [identity]
# please make sure you are at project root (i.e. ProtAgent)



# check parameter usage
if [ "$#" -lt 4 ] || [ "$#" -gt 5 ]; then
    echo "Usage: mmseqs_search.sh <MMSEQ_PATH> <QUERY_FASTA_PATH> <TARGET_FASTA_PATH> <ALIGN_FASTA_PATH> [identity]"
    exit 1
fi

WORKING_PATH=$(pwd)/outputs/mmseqs

make_absolute_path() {
  local path=$1
  if [[ $path = /* ]]; then
    echo "$path"
  else
    echo "$(realpath "../../../$path")"
  fi
}

# save DB files in DB dir
DB_DIR=$WORKING_PATH/database
TMP_DIR=$WORKING_PATH/tmp
identity=${5:-0.5}

echo "Runing MMseqs to search sequences in $3 which are similar to sequences in $2, with the identity threshold $identity"

# check dir
current_path=$(pwd)
echo "current_path=$current_path"
if [ $(basename $current_path) != "ProtAgent" ]; then
    echo "Please make sure you are at project root (i.e. ProtAgent)"
    exit 1
fi

if [ -d $DB_DIR ]; then
    echo "DB_DIR exists, remove it"
    echo "Be careful, this will remove all files in $DB_DIR"
    read -p "Press any key to continue, or press Ctrl+C to exit"
    rm -rf $DB_DIR
fi

if [ -d $TMP_DIR ]; then
    echo "TMP_DIR exists, remove it"
    echo "Be careful, this will remove all files in $TMP_DIR"
    read -p "Press any key to continue, or press Ctrl+C to exit"
    rm -rf $TMP_DIR
fi

mkdir -p $DB_DIR
mkdir -p $TMP_DIR

# save DB files in DB dir
cd $DB_DIR

MMSEQS=$(make_absolute_path "$1")
QUERY_FASTA_PATH=$(make_absolute_path "$2")
TARGET_FASTA_PATH=$(make_absolute_path "$3")
ALIGN_FASTA_PATH=$(make_absolute_path "$4")

# create query DB
$MMSEQS createdb $QUERY_FASTA_PATH queryDB
# create target DB
$MMSEQS createdb $TARGET_FASTA_PATH targetDB
# search
$MMSEQS search queryDB targetDB alignDB $TMP_DIR --min-seq-id $identity --alignment-mode 3 --max-seqs 300 -s 7 -c 0.8 --cov-mode 0
# convert result to fasta-like format
$MMSEQS convertalis queryDB targetDB alignDB $ALIGN_FASTA_PATH --format-output query

rm -rf $DB_DIR
rm -rf $TMP_DIR
