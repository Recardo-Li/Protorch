mkdir -p dataset
cd dataset

mkdir -p hmm
cd hmm

echo "Downloading Pfam-A.hmm.gz..."
wget http://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.hmm.gz
echo "Uncompressing the database..."
gunzip Pfam-A.hmm.gz
echo "Indexing the database with hmmpress..."
hmmpress Pfam-A.hmm
