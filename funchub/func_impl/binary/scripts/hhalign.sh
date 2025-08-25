#!/bin/bash

# use case: hhalign.sh -input1 <INPUT1> -input2 <INPUT2> [OPTIONS]
# please make sure you are at project root (i.e. ProtAgent)

# Default parameter values
input1="examples/fasta/binary/hhblits_alignment.a3m"
input2="examples/fasta/binary/hhfilter_output.a3m"
evalue=1e-3
qid=0
cov=0
a3m_result="outputs/binary/hhalign_output.a3m"

HHALIGN="bin/Umol/hh-suite/build/bin/hhalign"

# Parse arguments
for arg in "$@"
do
    case $arg in
        input1=*) input1="${arg#*=}" ;;
        input2=*) input2="${arg#*=}" ;;
        evalue=*) evalue="${arg#*=}" ;;
        qid=*) qid="${arg#*=}" ;;
        cov=*) cov="${arg#*=}" ;;
        a3m_result=*) a3m_result="${arg#*=}" ;;
        HHALIGN=*) HHALIGN="${arg#*=}" ;;
        *) ;;
    esac
done

# Check if required parameters are provided
if [ -z "$input1" ] || [ -z "$input2" ]; then
    echo "Usage: hhalign.sh -input1 <INPUT1> -input2 <INPUT2> [OPTIONS]"
    echo "Required parameters:"
    echo "  -input1: The first input file (HMM or MSA)."
    echo "  -input2: The second input file (HMM or MSA)."
    exit 1
fi

# Log the execution
echo "Running hhalign to align $input1 and $input2 with results saved to  $a3m_result"

# Check directory
current_path=$(pwd)
echo "current_path=$current_path"
if [ $(basename "$current_path") != "ProtAgent" ]; then
    echo "Please make sure you are at project root (i.e. ProtAgent)"
    exit 1
fi

# Run hhalign
$HHALIGN -i "$input1" -t "$input2" -oa3m "$a3m_result" -e $evalue -qid $qid -cov $cov

if [ $? -eq 0 ]; then
    echo "hhalign successfully completed. Output saved to $a3m_result."
else
    echo "hhalign encountered an error. Please check your inputs and options."
    exit 1
fi
