import argparse
import re
from gradio_client import Client
import pandas as pd

def protrek_search(input, input_type, query_type, db, csv_path, subsection_type="Function"):
    client = Client("http://search-protrek.com/")
    result = client.predict(
            input=input,
            nprobe=1000,
            topk=1,
            input_type=input_type,
            query_type=query_type,
            subsection_type=subsection_type,
            db=db,
            api_name="/search"
    )
    full_res = result[-1]["value"]
    columns = full_res["headers"]
    data = full_res["data"]
    # transfer np.float to float
    df = pd.DataFrame(data, columns=columns)
    df.to_csv(csv_path, index=False)

def get_args():
    parser = argparse.ArgumentParser(description="ProTrek search")
    parser.add_argument("--input_type", type=str, required=True, help="The type of the query, e.g. 'protein' or 'text'.")
    parser.add_argument("--query_type", type=str, required=True, help="The type of the result, e.g. 'protein' or 'text'.")
    parser.add_argument("--query", type=str, required=True, help="The natural language text description of a protein or the amino acid sequence of the protein.")
    parser.add_argument("--database", type=str, required=True, help="The specific database to search for the protein description, e.g. 'UniProt'.")
    parser.add_argument("--csv_path", type=str, required=True, help="The path to save the search result.")
    parser.add_argument("--subsection", type=str, required=False, help="The specific subsection of the database to search for the protein description, e.g. 'Function'.")
    return parser.parse_args()

def main(args):
    if args.subsection is None:
        protrek_search(args.query, args.input_type, args.query_type, args.database, args.csv_path)
    else:
        protrek_search(args.query, args.input_type, args.query_type, args.database, args.csv_path, args.subsection)
    
if __name__ == "__main__":
    """
    EXAMPLE:
    python cmd.py   --input_type sequence \
                    --query_type structure \
                    --query MRLGSVFLVLLVLLGLGAGVAAVPGLG \
                    --database Swiss-Prot \
                    --csv_path result.csv
    """
    args = get_args()
    main(args)