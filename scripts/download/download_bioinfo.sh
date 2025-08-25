# install hmmer
apt-get update
apt-get install -y hmmer


cd funchub/func_impl/bioinfo
mkdir bin
cd bin

# install mmseqs
wget https://mmseqs.com/latest/mmseqs-linux-avx2.tar.gz
tar xvzf mmseqs-linux-*.tar.gz

# install clustalw
wget http://www.clustal.org/download/current/clustalw-2.1-linux-x86_64-libcppstatic.tar.gz
tar xvzf clustalw*.tar.gz

