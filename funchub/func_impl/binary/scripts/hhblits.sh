#!/bin/bash

# use case: hhblits.sh -i <FASTA_FILE> -o <OUTPUT_FILE>[OPTIONS]
# please make sure you are at project root (i.e. ProtAgent)

# Default parameter values
query_sequence="examples/fasta/binary/7NB4.fasta"
n_iter=2
evalue=1e-3
alignment_file="outputs/binary/hhblits_alignment.a3m"

UNICLUST="dataset/Umol/uniclust30_2018_08/uniclust30_2018_08"
HHBLITS="bin/Umol/hh-suite/build/bin/hhblits"

# Parse arguments
for arg in "$@"
do
    case $arg in
        query_sequence=*) query_sequence="${arg#*=}" ;;
        n_iter=*) n_iter="${arg#*=}" ;;
        evalue=*) evalue="${arg#*=}" ;;
        alignment_file=*) alignment_file="${arg#*=}" ;;
        HHBLITS=*) HHBLITS="${arg#*=}" ;;
        *) ;;
    esac
done

# Check if required parameters are provided
if [ -z "$query_sequence" ]; then
    echo "Usage: hhblits.sh -i <QUERY_SEQUENCE> [OPTIONS]"
    echo "Required parameters:"
    echo "  -i: The protein sequence used as the query for homology searches."
    exit 1
fi

# Log the execution
echo "Running hhblits to search query sequence against protein database with results saved to $alignment_file"

# Check directory
current_path=$(pwd)
echo "current_path=$current_path"
if [ $(basename "$current_path") != "ProtAgent" ]; then
    echo "Please make sure you are at project root (i.e. ProtAgent)"
    exit 1
fi

# Run hhblits
$HHBLITS -i "$query_sequence" -oa3m "$alignment_file" -n $n_iter -e $evalue -d $UNICLUST

if [ $? -eq 0 ]; then
    echo "hhblits successfully completed. Output saved to $alignment_file."
else
    echo "hhblits encountered an error. Please check your inputs and options."
    exit 1
fi
