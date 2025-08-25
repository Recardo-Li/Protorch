#!/bin/bash

# use case: hhfilter.sh -i <INFILE> -o <OUTFILE> [OPTIONS]
# please make sure you are at project root (i.e. ProtAgent)

# check parameter usage

input_msa="examples/fasta/binary/hhblits_alignment.a3m"
id=90
cov=50
diff=1000
filtered_msa="outputs/binary/hhfilter_output.a3m"

HHFILTER="bin/Umol/hh-suite/build/bin/hhfilter"

for arg in "$@"
do
    case $arg in
        input_msa=*) input_msa="${arg#*=}" ;;
        id=*) id="${arg#*=}" ;;
        cov=*) cov="${arg#*=}" ;;
        diff=*) diff="${arg#*=}" ;;
        filtered_msa=*) filtered_msa="${arg#*=}" ;;
        HHFILTER=*) HHFILTER="${arg#*=}" ;;
        *) ;;
    esac
done

# Check if required parameters are provided
if [ -z "$input_msa" ] || [ -z "$filtered_msa" ]; then
    echo "Usage: hhfilter.sh -i <INFILE> -o <OUTFILE> [OPTIONS]"
    echo "Required parameters:"
    echo "-input_msa: The input multiple sequence alignment (MSA) file, typically in A3M format, to be filtered."
    exit 1
fi

echo "Running hhfilter to process alignment file $input_msa"

# check directory
current_path=$(pwd)
echo "current_path=$current_path"
if [ $(basename "$current_path") != "ProtAgent" ]; then
    echo "Please make sure you are at project root (i.e. ProtAgent)"
    exit 1
fi

# run hhfilter
$HHFILTER -i $input_msa -o $filtered_msa -id $id -diff $diff -cov $cov

if [ $? -eq 0 ]; then
    echo "hhfilter successfully completed. Output saved to $filtered_msa."
else
    echo "hhfilter encountered an error. Please check your inputs and options."
    exit 1
fi
