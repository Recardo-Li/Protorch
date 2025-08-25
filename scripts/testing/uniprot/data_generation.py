import sys

sys.path.append(".")
import pandas as pd
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

def generate_data(tool_doc):
    sys_prompt, user_prompt, result, model = query_single_tool_for_caller(tool_doc, 1)
    if not os.path.exists("tmp"):
        os.makedirs("tmp")
    with open(f"tmp/tmp_data.json", "w") as f:
        f.write(json.dumps(result))
    convert_json_format("tmp/tmp_data.json")
    return "tmp/tmp_data.json"

def example_input(category, toolname):
    return f"examples/inputs/{category}/{category}_{toolname}_input.json"

def run(config):
    result = []
    cnt = 0
    toolset = load_toolset(config.toolset)
    selector = load_selector(config.selector, toolset)
    data_pipeline = DataPipeline(toolset, selector, config.caller_root)

    category = "uniprot"
    for toolname in toolset.tool_func_list[category].values():
        tool_doc_dir = os.path.join(toolset.doc_dir, category, f"{toolname}.json")
        tool_doc = json.load(open(tool_doc_dir, "r"))
        inputs = UserInput(generate_data(tool_doc)).raw_inputs
        for raw_input in inputs:
            cnt += 1
            print(f"processing {cnt}th question")
            
            data_pipeline.process_select(raw_input)

            if data_pipeline.selection[0] != category:
                print(
                    f"\033[31m{category} is not selected, while {data_pipeline.selection[0]} is selected as a best choice\033[0m"
                )

            if data_pipeline.selection[1] != toolname:
                print(
                    f"\033[31m{toolname} is not selected, while {data_pipeline.selection[1]} is selected as a best choice\033[0m"
                )

            data_pipeline.selection = (category, toolname)
            data_pipeline.process_call(raw_input)
            output = data_pipeline.process_result()
            result.append(
                {
                    "seq_name": raw_input.values["uniprot_id"],
                    "comment_type": "qa_gen_func",
                    "pred_sentence": output,
                    "answer_sentence": "GROUND_TRUTH",
                    "question_sentence": raw_input.values["question"],
                }
            )
            # print(f"finish processing {cnt}th question")

        output_dir = os.path.dirname(config.data.output)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(os.path.join(output_dir, f"{category}_{toolname}.json"), "w") as f:
            f.write("\t".join("seq_name", "comment_type", "pred_sentence", "answer_sentence", "question_sentence"))
            f.write("\n")
            for res in result:
                f.write("\t".join(res.values()))
                f.write("\n")
            


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default="outputs/uniprot/uniprot_qa_1017.json")
    args = parser.parse_args()
    main(args)
