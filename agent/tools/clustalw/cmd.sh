#!/bin/bash

# use case: clustalw.sh <FASTA_PATH> <ALN_PATH>
# please make sure you are at project root (i.e. ProtAgent)


# check parameter usage
if [ "$#" -ne 3 ]; then
    echo "Usage: clustalw.sh <CLUSTAL_PATH> <FASTA_PATH> <ALN_PATH>"
    exit 1
fi
echo "Runing ClustalW to align sequences in FASTA files in $2 to $3"

# check dir
current_path=$(pwd)
echo "current_path=$current_path"
if [ $(basename $current_path) != "ProtAgent" ]; then
    echo "Please make sure you are at project root (i.e. ProtAgent)"
    exit 1
fi


FASTA_PATH=$2
ALN_PATH=$3
CLUSTALS=$1

$CLUSTALS -INFILE=$FASTA_PATH -OUTFILE=$ALN_PATH