#!/bin/bash

# use case: mmseq_group.sh <FASTA_PATH> <GROUP_FASTA_PATH> [identity]
# please make sure you are at project root (i.e. ProtAgent)


WORKING_PATH=$(pwd)/outputs/mmseqs

make_absolute_path() {
  local path=$1
  if [[ $path = /* ]]; then
    echo "$path"
  else
    echo "$(realpath "../../../$path")"
  fi
}

WORKING_PATH=$(pwd)/outputs/mmseqs

# check parameter usage
if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
    echo "Usage: mmseq_group.sh <MMSEQ_PATH> <FASTA_PATH> <GROUP_FASTA_PATH> [identity]"
    exit 1
fi

# save DB files in DB dir
DB_DIR=$WORKING_PATH/database
TMP_DIR=$WORKING_PATH/tmp
identity=${4:-0.5}


echo "Runing MMseqs to group sequences in FASTA files in $2 to $3, with the identity threshold $identity"

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

cd $DB_DIR

MMSEQS=$(make_absolute_path "$1")
FASTA_PATH=$(make_absolute_path "$2")
GROUP_FASTA_PATH=$(make_absolute_path "$3")


# create DB
$MMSEQS createdb $FASTA_PATH DB
# cluster
$MMSEQS cluster DB DB_clu $TMP_DIR --min-seq-id $identity
# save representative sequence
$MMSEQS createseqfiledb DB DB_clu DB_clu_seq
# convert result to fasta-like format
$MMSEQS result2flat DB DB DB_clu_seq $GROUP_FASTA_PATH

rm -rf $DB_DIR
rm -rf $TMP_DIR
