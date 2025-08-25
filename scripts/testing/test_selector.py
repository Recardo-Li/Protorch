from pathlib import Path
import sys

sys.path.append(".")

import pandas as pd
import json
import argparse
import data.globalvar as globalvar
from data.data_pipeline import DataPipeline
from data.raw_input import UserInput
from prompts.generate_query_tool import convert_json_format, query_single_tool_for_caller
from utils.seed import setup_seed
from utils.module_loader import *
from config import *
from fairscale.nn.model_parallel.initialize import initialize_model_parallel
import os


def generate_data(tool_doc):
    sys_prompt, user_prompt, result, model = query_single_tool_for_caller(tool_doc, 1)
    if not os.path.exists("tmp"):
        os.makedirs("tmp")
    with open(f"tmp/tmp_data.json", "w") as f:
        f.write(json.dumps(result))
    convert_json_format("tmp/tmp_data.json")
    return "tmp/tmp_data.json"

inProgress = ["structure_prediction", "protein_design"]
def make_input_file(toolset: ToolSet, input_file="examples/inputs/all_input.json"):
    all_inputs = None
    for category in toolset.tool_dict.keys():
        if category in inProgress:
            continue
        if not os.path.exists(f"examples/inputs/{category}"):
            for toolname in toolset.tool_func_dict[category].keys():
                tool_doc_dir = os.path.join(toolset.doc_dir, category, f"{toolname}.json")
                tool_doc = json.load(open(tool_doc_dir, "r"))
                inputs = UserInput(generate_data(tool_doc))
                inputs.save(input_file, "a")
                if all_inputs is None:
                    all_inputs = inputs
                else:
                    all_inputs.extend(inputs)
        else:
            for example_path in Path(f"examples/inputs/{category}").rglob("*.json"):
                inputs = UserInput(example_path)
                inputs.save(input_file, "a")
                if all_inputs is None:
                    all_inputs = inputs
                else:
                    all_inputs.extend(inputs)
    all_inputs.save(input_file)

def run(config):
    result = []
    cnt = 1
    tool_correct = 0  # Count of correct tool selections
    category_correct = 0  # Count of correct category selections
    total = 0  # Total number of questions
    wrong_category_cases = []  # Store cases where category selection is wrong
    wrong_tool_cases = []  # Store cases where tool selection is wrong

    toolset = load_toolset(config.toolset)
    selector = load_selector(config.selector, toolset)
    data_pipeline = DataPipeline(toolset, selector, config.caller_root)

    for raw_input in UserInput(config.data.input).raw_inputs:
        print(f"Processing {cnt}th question")
        cnt += 1
        total += 1
        data_pipeline.process_select(raw_input)
        selected_category = data_pipeline.selection[0]
        selected_tool = data_pipeline.selection[1]
        question = raw_input.values["question"]

        result.append(
            {
                "question": question,
                "tool": selected_tool,
                "category": selected_category,
            }
        )

        # Check if category selection is correct
        if selected_category == raw_input.values["category"]:
            category_correct += 1
            print(f"\033[32m{selected_category} is correctly selected\033[0m")
        else:
            print(f"\033[31m{selected_category} is incorrectly selected\033[0m")
            # Save cases where category selection is wrong
            wrong_category_cases.append({
                "question": question,
                "selected_category": selected_category,
                "correct_category": raw_input.values["category"]
            })

        # Check if tool selection is correct
        if selected_tool == raw_input.values["tool"]:
            tool_correct += 1
            print(f"\033[32m{selected_tool} is correctly selected\033[0m")
        else:
            print(f"\033[31m{selected_tool} is incorrectly selected\033[0m")
            # Save cases where tool selection is wrong
            wrong_tool_cases.append({
                "question": question,
                "selected_tool": selected_tool,
                "correct_tool": raw_input.values["tool"]
            })

        print(f"Finished processing {cnt}th question")

    # Calculate accuracy
    tool_accuracy = tool_correct / total * 100
    category_accuracy = category_correct / total * 100

    print(f"\nTool selection accuracy: {tool_accuracy:.2f}%")
    print(f"Category selection accuracy: {category_accuracy:.2f}%\n")

    # Save results
    output_dir = os.path.dirname(config.data.output)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    json.dump(result, open(config.data.output, "w"), indent=4)

    # Create the directory for storing wrong selections
    error_output_dir = os.path.join(output_dir, "selector_test_details")
    if not os.path.exists(error_output_dir):
        os.makedirs(error_output_dir)

    # Save wrong category selection cases to a CSV file
    if wrong_category_cases:
        wrong_category_df = pd.DataFrame(wrong_category_cases)
        wrong_category_df.to_csv(os.path.join(error_output_dir, "wrong_category.csv"), index=False)

    # Save wrong tool selection cases to a CSV file
    if wrong_tool_cases:
        wrong_tool_df = pd.DataFrame(wrong_tool_cases)
        wrong_tool_df.to_csv(os.path.join(error_output_dir, "wrong_tool.csv"), index=False)


def main(args):
    if args.public:
        config = cfg_inference_public
    else:
        config = cfg_inference_local

    if config.data_dir:
        globalvar.huggingface_root = Path(config.data_dir.huggingface_root)
        globalvar.bin_root = Path(config.data_dir.bin_root)
        globalvar.modelhub_root = Path(config.data_dir.modelhub_root)
        globalvar.dataset_root = Path(config.data_dir.dataset_root)
    else:
        # Set to local folder by default
        globalvar.huggingface_root = Path("huggingface")
        globalvar.bin_root = Path("bin")
        globalvar.modelhub_root = Path("modelhub")
        globalvar.dataset_root = Path("dataset")

    if config.setting.seed:
        print("Setting up random seed")
        setup_seed(config.setting.seed)

    # Set OS environment variables
    print("Setting up OS environment variables")
    for k, v in config.setting.os_environ.items():
        if v is not None and k not in os.environ:
            os.environ[k] = str(v)
        elif k in os.environ:
            # Override the OS environment variables
            config.setting.os_environ[k] = os.environ[k]

    # Only the root node will print the log
    if config.setting.os_environ.NODE_RANK != 0:
        config.Trainer.logger = False

    # Update config data input and output
    if args.input is None:
        make_input_file(load_toolset(config.toolset))
        args.input = "examples/inputs/all_input.json"
    else:
        config.data.input = args.input
    config.data.output = args.output


    run(config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=bool, default=True)
    parser.add_argument("--input", type=str, default=None)
    parser.add_argument("--output", type=str, default="outputs/selector_output.json")
    args = parser.parse_args()
    main(args)
