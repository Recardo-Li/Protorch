#!/bin/bash

# use case: hmmbuild.sh <ALN_PATH> <HMM_PATH>
# please make sure you are at project root (i.e. ProtAgent)


# check parameter usage
if [ "$#" -ne 3 ]; then
    echo "Usage: hmmbuild.sh <HMMBUILD_PATH> <ALN_PATH> <HMM_PATH>"
    exit 1
fi
echo "Runing hmmer to build HMM from alignment files in $2 to $3"

# check dir
current_path=$(pwd)
echo "current_path=$current_path"
if [ $(basename $current_path) != "ProtAgent" ]; then
    echo "Please make sure you are at project root (i.e. ProtAgent)"
    exit 1
fi


ALN_PATH=$2
HMM_PATH=$3
HMMBUILD=$1


$HMMBUILD $HMM_PATH $ALN_PATH
