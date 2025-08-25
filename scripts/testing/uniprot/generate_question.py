import json
import random
import os
import glob

import pandas as pd

import re
import sys

sys.path.append("/root/ProtAgent")
from funchub.func_impl.uniprot.uniprot import get_record, uniprot_QA
from model.tool_caller.uniprot_caller import UniprotCaller

from prompts.utils.mpr import MultipleProcessRunnerSimplifier
from prompts.utils.api_utils import APIPool, api_urls
from prompts.utils.prompt_utils import Prompts

api_pool = APIPool(api_urls)
import time
import argparse
from prompts.utils.adjust_generated_query import adjust_query_saprot_mutation

import json
import argparse

from pathlib import Path

import data.globalvar as globalvar
from data.data_pipeline import DataPipeline
from data.raw_input import UserInput
from utils.seed import setup_seed
from utils.module_loader import *
from prompts.generate_query_tool import (
    query_single_tool_for_caller,
    convert_json_format,
)
from config import *

SUBSECTIONS = [
                "Active site",
                "Activity regulation",
                "Allergenic properties",
                "Binding site",
                "Biophysicochemical properties",
                "Biotechnology",
                "Catalytic activity",
                "Caution",
                "Chain",
                "Cofactor",
                "Coiled coil",
                "Compositional bias",
                "Cross-link",
                "DNA binding",
                "Developmental stage",
                "Disruption phenotype",
                "Disulfide bond",
                "Domain (non-positional annotation)",
                "Domain",
                "Function",
                "GO annotation",
                "Gene names",
                "Glycosylation",
                "Induction",
                "Intramembrane",
                "Involvement in disease",
                "Lipidation",
                "Miscellaneous",
                "Modified residue",
                "Motif",
                "Mutagenesis",
                "Natural variant",
                "Organism",
                "Pathway",
                "Peptide",
                "Pharmaceutical use",
                "Polymorphism",
                "Post-translational modification",
                "Propeptide",
                "Protein names",
                "Proteomes",
                "RNA Editing",
                "Region",
                "Repeat",
                "Sequence similarities",
                "Signal peptide",
                "Site",
                "Subcellular location",
                "Subunit",
                "Taxonomic lineage",
                "Tissue specificity",
                "Topological domain",
                "Toxic dose",
                "Transit peptide",
                "Transmembrane",
                "Virus host"
            ]

def query_single_tool_for_caller(tool_doc, id, subsection, no_of_queries):
    """add few shots"""
    
    sys_prompt = Prompts.get_sys_prompt_for_caller_optional_paras(
        no_of_queries=no_of_queries
    )

    user_prompt = f"""Now you need to generate the input for the tool uniprot_qa in the category uniprot.

{tool_doc}

In this json, "tool" is specificated to "uniprot_qa" and "category" is specificated to "uniprot". And all the parameters needs to be aligned with the documentations. And make sure the id is {id}, the subsection is {subsection}. Please generate the json string for us.
"""
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]
    result, model = api_pool.get_response(messages)
    return sys_prompt, user_prompt, result, model

def do_for_caller(process_id, datum_id, datum, w):
    for subsection in SUBSECTIONS:
        sys_prompt, user_prompt, result, model = query_single_tool_for_caller(
            tool_doc, datum, subsection, 9
        )
        tmp_question_path = f"outputs/uniprot/questions/{subsection}.json"
        
        with open(tmp_question_path, "r") as f:
            querys = json.load(f)
            question_only = []
            if len(querys) == 10:
                for query in querys:
                    question_only.append(query["question"])
                with open(f"outputs/uniprot/question_tsv/{subsection}.tsv", "w") as tsv_f:
                    tsv_f.write("\n".join(question_only))
                continue
        
        with open(tmp_question_path, "a") as f:
            f.write(json.dumps(result))
        convert_json_format(tmp_question_path)
        # inputs = UserInput(tmp_question_path).raw_inputs
        
        # answerpath="funchub/func_impl/uniprot/templates/text_template_new.json"
        # paragraph2sentencepath="funchub/func_impl/uniprot/templates/paragraph_to_sentences_dict.json"
        # paraphrasepath="funchub/func_impl/uniprot/templates/paraphrased_sentences.json"
        
        # for raw_input in inputs:
        #     caller_output = uniprot_QA(
        #             raw_input.values["subsection"],
        #             raw_input.values["uniprot_id"],
        #             json.load(open(answerpath)),
        #             json.load(open(paragraph2sentencepath)),
        #             json.load(open(paraphrasepath)),
        #         )
        #     if "Not found" in caller_output:
        #         continue
        #     w.write('\t'.join([raw_input.values["uniprot_id"], "qa_gen_func", caller_output, "GROUND_TRUTH", raw_input.values["question"]]))
        #     w.write('\n')
        
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_process", type=int, default=1)
    parser.add_argument(
        "--no_of_queries",
        type=int,
        default=3,
        help="How many queries should be generated for each tool.",
    )
    parser.add_argument("--output", type=str, default="outputs/uniprot/uniprot_qa.tsv", help="The path of the output data")

    args = parser.parse_args()
    return args


def convert_json_format(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        file_content = f.read()
    # matches = re.findall(r'\{[^{}]*\}', file_content)  # find all {}
    matches = re.findall(r"\{.*?\}", file_content, re.DOTALL)
    json_objects = []
    for match in matches:
        clean_match = match.replace(",\\n  }", "\\n  }")
        clean_match = clean_match.replace(",\\n }", "\\n }")
        clean_match = clean_match.replace("\\n", "")
        clean_match = clean_match.replace("\\", "")
        # cleaned_match = re.sub(r',\s*$', '', match, flags=re.MULTILINE)
        # print("processing...\n", clean_match)
        # import pdb; pdb.set_trace()
        json_objects.append(json.loads(clean_match))

    with open(file_path, "w") as f:
        json.dump(json_objects, f, indent=2)

    # print("JSON objects have been converted to right format.")


def run(config):
    do = do_for_caller

    # save_path = config.data.output
    
    # input_data = pd.read_csv("/root/ProtAgent/scripts/testing/uniprot/test.tsv", sep="\t").values.tolist()
    # mpr = MultipleProcessRunnerSimplifier(
    #     data=input_data,
    #     do=do,
    #     save_path=save_path,
    #     n_process=n_process,
    #     split_strategy="queue",
    # )
    # mpr.run()
    do(0, 0, "P0A7B8", open("scripts/testing/uniprot/questions", "a"))


def main(args):
    
    config = cfg_inference_public

    if config.data_dir:
        globalvar.huggingface_root = Path(config.data_dir.huggingface_root)
        globalvar.bin_root = Path(config.data_dir.bin_root)
        globalvar.modelhub_root = Path(config.data_dir.modelhub_root)
        globalvar.dataset_root = Path(config.data_dir.dataset_root)
    else:
        # set to local folder by default
        globalvar.huggingface_root = Path("huggingface")
        globalvar.bin_root = Path("bin")
        globalvar.modelhub_root = Path("modelhub")
        globalvar.dataset_root = Path("dataset")

    if config.setting.seed:
        print("setting up random seed")
        setup_seed(config.setting.seed)

    # set os environment variables
    print("setting up os environment variables")
    for k, v in config.setting.os_environ.items():
        if v is not None and k not in os.environ:
            os.environ[k] = str(v)

        elif k in os.environ:
            # override the os environment variables
            config.setting.os_environ[k] = os.environ[k]

    # Only the root node will print the log
    if config.setting.os_environ.NODE_RANK != 0:
        config.Trainer.logger = False

    # Update config data input and output
    config.data.output = args.output

    run(config)



if __name__ == "__main__":

    args = parse_args()
    n_process = args.n_process
    no_of_queries = args.no_of_queries
    tool_doc_dir = "funchub/func_doc/uniprot/uniprot_qa.json"
    tool_doc = json.load(open(tool_doc_dir, "r"))
    main(args)
