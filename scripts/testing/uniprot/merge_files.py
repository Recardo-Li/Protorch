import os

with open("outputs/uniprot/uniprot_qa.tsv", "w") as f:
    f.write("\t".join(["uniprot_id", "comment_type", "pred_sentence", "answer_sentence", "question_sentence"]))

for file in os.listdir("outputs/uniprot/uniprot_qa.tsv_temp"):
    with open(f"outputs/uniprot/uniprot_qa.tsv_temp/{file}", "r") as f:
        data = f.read()
    
    # remove empty lines
    data = "\n".join([line for line in data.split("\n") if line.strip()])
    with open("outputs/uniprot/uniprot_qa.tsv", "a") as f:
        f.write(data)
        f.write("\n")