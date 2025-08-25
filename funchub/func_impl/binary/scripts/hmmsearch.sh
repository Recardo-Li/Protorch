#!/bin/bash

# use case: hmmsearch.sh <RES_PATH> <HMM_PATH> <FASTA_PATH>
# please make sure you are at project root (i.e. ProtAgent)


# check parameter usage
if [ "$#" -lt 4 ] || [ "$#" -gt 5 ]; then
    echo "Usage: hmmsearch.sh <HMMSEARCH_PATH> <RES_PATH> <HMM_PATH> <FASTA_PATH> [domE]"
    exit 1
fi

RES_PATH=$2
HMM_PATH=$3
FASTA_PATH=$4
domE=${5:-0.1}
HMMSEARCH=$1

echo "Runing hmmer to annotate function domain for $4, using $3, result is saved to $2, with domE=$domE"

# check dir
current_path=$(pwd)
echo "current_path=$current_path"
if [ $(basename $current_path) != "ProtAgent" ]; then
    echo "Please make sure you are at project root (i.e. ProtAgent)"
    exit 1
fi


$HMMSEARCH --domE $domE --domtblout $RES_PATH $HMM_PATH $FASTA_PATH
