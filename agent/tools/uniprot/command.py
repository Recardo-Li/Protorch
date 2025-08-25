import argparse
import json
import os
import requests
import random
import urllib.parse

import sys
import time

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from agent.tools.uniprot.uniprot.record_process import record2text
from agent.tools.uniprot.uniprot.entry_process import extract_texts
from agent.tools.uniprot.uniprot.configs import paraphrased_subsection
from agent.tools.uniprot.constant import subsection_classes

HEADER_DICT = {
    "json": "application/json",
    "xml": "application/xml",
    "txt": "text/plain; format=flatfile",
    "list": "text/plain; format=list",
    "tsv": "text/plain; format=tsv",
    "fasta": "text/plain; format=fasta",
    "gff": "text/plain; format=gff",
    "obo": "text/plain; format=obo",
    "rdf": "application/rdf+xml",
    "xlsx": "application/vnd.ms-excel"
}

RETRY_LIMIT = 3
RECORDS_PER_PAGE = 500
DEFAULT_RECORDS = 25

def web_query_uniprot(id):
    try:
        with requests.Session() as uniprot_api: 
            results = uniprot_api.get(f"https://rest.uniprot.org/uniprotkb/{id}.json")
            results = results.json()
            return results
    except:
        return None

def get_record(id, subsection):
    data_dict = web_query_uniprot(id)
    if data_dict is None:
        return None
    records = extract_texts(data_dict)
    if subsection not in subsection_classes:
        print(f"Subsection {subsection} invalid. Valid subsections are: {list(subsection_classes.keys())}", flush=True)
        return []
    else:
        results = []
        for name in subsection_classes[subsection]:
            print(f"Extracting records for subsection: {name}", flush=True)
            results.extend([record for record in records if record[3] == name])
    return results


def uniprot_query(record, answers_template, paragraph2sentence, paraphrase):
    sequence_name, aa_length, section, subsection, _, raw_text, note = record
    # get answer
    text, raw_text_list = record2text(record, answers_template)
    if len(raw_text_list) == 0:
        raw_text_list = [text]
    if isinstance(text, list):
        idx = random.choice(range(len(text)))
        text = text[idx]
        raw_text_list = raw_text_list[idx]

    if subsection in paraphrased_subsection and text == raw_text:
        try:
            if text in paragraph2sentence[subsection]:
                sentences = paragraph2sentence[subsection][text]
            else:
                sentences = [text]
            sentence = random.choice(sentences)
            text = random.choice(
                paraphrase[subsection][sentence]
                + len(paraphrase[subsection][sentence]) * [sentence]
            )  # half is original, half is paraphrased
        except:
            print(subsection, flush=True)
            print(text, flush=True)
    return text, raw_text_list

def uniprot_QA(subsection, id, answers_template, paragraph2sentence, paraphrase):
    records = get_record(id, subsection)
    if len(records) == 0:
        return f"Subsection {subsection} of Protein {id} Not found"
    result_list = []
    for record in records:
        text, raw_text = uniprot_query(
            record, answers_template, paragraph2sentence, paraphrase
        )
        if text is not None:
            result_list.append(text)
    return result_list

def fetch_sequence(uniprot_id):
    url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.fasta"
    requests_return = requests.get(url)
    splits = requests_return.text.split("\n")
    sequence = "".join(splits[1:]).strip()
    return sequence

def fetch_structure(uniprot_id, save_dir):
    url = f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb"
    if os.path.exists(save_dir) is False:
        print(f'"error": "Directory {save_dir} does not exist"', flush=True)
        return ""
    save_path = f"{save_dir}/{uniprot_id}.pdb"
    wget = f"wget -q -o /dev/null {url} -O {save_path}"
    os.system(wget)
    return save_path

def restful_query(query, save_path):
    print("Trying to query UniProt with query:", query, flush=True)
    print("We will return the first 25 records (at most)", flush=True)
    params = {
        "query": query,
        "format": "json",
        "size": DEFAULT_RECORDS
    }
    url = "https://rest.uniprot.org/uniprotkb/search"
    header = {"Accept": HEADER_DICT["json"]}
    
    try:
        for _ in range(RETRY_LIMIT):
            response = requests.get(url, params=params, headers=header)
            if response.status_code != 200:
                print(f"Network error: {response.status_code}. Retrying...", flush=True)
                time.sleep(0.1)
            else:
                break
        if response.status_code != 200:
            return {"record_num": 0, "error": f"Network error: {response.status_code}"}
        
        data = response.json()
        if "results" not in data:
            return {"record_num": 0, "error": "No results found"}

        # Save results to file
        with open(save_path, 'w') as f:
            json.dump(data["results"], f, indent=4)
        
        return {"record_num": len(data["results"])}
    except Exception as e:
        return {"record_num": 0, "error": str(e)}

def restful_query_all(query, save_path):
    """
    Query UniProt REST API with pagination support.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to retrieve. 
                    If -1, retrieves all results.
                    If 0, uses default API limit (usually 25).
                    Default is 2000.
    
    Returns:
        Combined JSON response with all results
    """
    print("Trying to query UniProt with query:", query, flush=True)
    print("We will return all records, so this will take a while...", flush=True)

    all_results = []
    next_url = None
    
    while True:
        params = {
            "query": query,
            "format": "json",
            "size": RECORDS_PER_PAGE
        }
        url = "https://rest.uniprot.org/uniprotkb/search"
        headers = {"Accept": HEADER_DICT["json"]}

        for _  in range(RETRY_LIMIT):
            try:
                if not next_url:
                    response = requests.get(url, params=params, headers=headers)
                else:
                    response = requests.get(next_url, headers=headers)
                if response.status_code != 200:
                    print(f"Network error: {response.status_code}. Retrying...", flush=True)
                    continue
                else:
                    break
            except Exception as e:
                print(f"Request failed: {e}. Retrying...", flush=True)
                time.sleep(0.1)
            
        data = response.json()
        all_results.extend(data.get("results", []))

        print("Fetched {} records so far...".format(len(all_results)), flush=True)

        # Save results to file
        with open(save_path, 'w') as f:
            json.dump(all_results, f, indent=4)
            
        link_str = response.headers.get("Link", None)

        if link_str is None:
            break
        else:
            next_url = link_str.split(";")[0].strip("<>")
        
    return {"record_num": len(all_results)}


def main(args):
    if args.query:
        query = args.query
        all_results = getattr(args, 'all_results', False)
        if not all_results:
            result = restful_query(query, save_path=f"{args.save_dir}/result.json")
        else:
            result = restful_query_all(query, save_path=f"{args.save_dir}/result.json")
        
        if result.get("error"):
            print(f"Error: {result['error']}", flush=True)
        if result.get("record_num"):
            print(f"Total records retrieved: {result['record_num']}", flush=True)
        else:
            print("Error retrieving records.", flush=True)
    else:
        result_dict = {}
        if args.subsection:
            answer_template = json.load(open(args.answers_template))
            paragraph2sentence = json.load(open(args.paragraph2sentence))
            paraphrase = json.load(open(args.paraphrase))
            subsection_result = uniprot_QA(
                args.subsection,
                args.id,
                answer_template,
                paragraph2sentence,
                paraphrase
            )
            result_dict["subsection_info"] = subsection_result
        structure_result = fetch_structure(args.id, args.save_dir)
        if os.path.exists(structure_result) and os.path.getsize(structure_result) > 0:
            result_dict["protein_structure"] = structure_result
        else:
            result_dict["protein_structure"] = "No structure found."
        sequence_result = fetch_sequence(args.id)
        result_dict["protein_sequence"] = sequence_result
        print(f"Uniprot items for {args.id}:", flush=True)
        print(json.dumps(result_dict, indent=4), flush=True)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=str)
    parser.add_argument("--query", type=str)
    parser.add_argument("--format", type=str, default="json")
    parser.add_argument("--subsection", type=str)
    parser.add_argument("--save_dir", type=str, default=".")
    parser.add_argument("--all_results", type=bool, default=False)
    parser.add_argument("--answers_template", type=str)
    parser.add_argument("--paragraph2sentence", type=str)
    parser.add_argument("--paraphrase", type=str)
    return parser.parse_args()

if __name__ == "__main__":
    """
    python command.py   --query "membrane AND reviewed:true AND proteins_with:1" \
                        --all_results True
    """
    args = get_args()
    main(args)