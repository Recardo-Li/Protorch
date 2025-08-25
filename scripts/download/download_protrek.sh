mkdir huggingface
cd huggingface
git lfs install

mkdir ProTrek
cd ProTrek
# Download ProTrek_650M_UniRef50
git clone https://huggingface.co/westlake-repl/ProTrek_650M_UniRef50

# Download faiss index
huggingface-cli download westlake-repl/faiss-index  --repo-type dataset  --local-dir . --include "Swiss-Prot/ProTrek_650M_UniRef50/text/subsections/*"


TARGET_DIR="ProTrek_650M_UniRef50/Swiss-Prot/text/subsections"

while true; do
    file_count=$(ls "$TARGET_DIR" | wc -l)
    
    if [ "$file_count" -lt 108 ]; then
        echo "File count is $file_count, which is less than 108. Downloading missing files..."
        
        huggingface-cli download westlake-repl/faiss-index \
            --repo-type dataset \
            --local-dir . \
            --include "Swiss-Prot/ProTrek_650M_UniRef50/text/subsections/*" \
            --resume-download
    else
        echo "File count has reached 108 or more. No further downloads needed."
        break
    fi
    
    sleep 10
done

cd ../..