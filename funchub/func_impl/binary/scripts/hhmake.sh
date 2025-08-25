#!/bin/bash

# use case: hhmake.sh -msa_file <MSA_FILE> [OPTIONS]
# please make sure you are at project root (i.e. ProtAgent)

# Default parameter values
msa_file="examples/fasta/binary/hhblits_alignment.a3m"
id=90
diff=100
cov=0
qid=0
qsc=-20.0
neff="off"
hmm_file="outputs/binary/hhmake_output.hmm"

HHMAKE="bin/Umol/hh-suite/build/bin/hhmake"

# Parse arguments
for arg in "$@"
do
    case $arg in
        msa_file=*) msa_file="${arg#*=}" ;;
        id=*) id="${arg#*=}" ;;
        diff=*) diff="${arg#*=}" ;;
        cov=*) cov="${arg#*=}" ;;
        qid=*) qid="${arg#*=}" ;;
        qsc=*) qsc="${arg#*=}" ;;
        neff=*) neff="${arg#*=}" ;;
        hmm_file=*) hmm_file="${arg#*=}" ;;
        HHMAKE=*) HHMAKE="${arg#*=}" ;;
        *) ;;
    esac
done

# Check if required parameters are provided
if [ -z "$msa_file" ]; then
    echo "Usage: hhmake.sh -msa_file <MSA_FILE> [OPTIONS]"
    echo "Required parameters:"
    echo "  -msa_file: The multiple sequence alignment (MSA) file in A3M format."
    exit 1
fi

# Log the execution
echo "Running hhmake to generate HMM from MSA $msa_file with results saved to $hmm_file"

# Check directory
current_path=$(pwd)
echo "current_path=$current_path"
if [ $(basename "$current_path") != "ProtAgent" ]; then
    echo "Please make sure you are at project root (i.e. ProtAgent)"
    exit 1
fi

# Run hhmake
$HHMAKE -i "$msa_file" -o "$hmm_file" -id $id -diff $diff -cov $cov -qid $qid -qsc $qsc -neff $neff

if [ $? -eq 0 ]; then
    echo "hhmake successfully completed. Output saved to $hmm_file."
else
    echo "hhmake encountered an error. Please check your inputs and options."
    exit 1
fi
