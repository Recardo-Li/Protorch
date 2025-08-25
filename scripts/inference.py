from pathlib import Path
import sys

sys.path.append(".")
import pandas as pd
import json
import argparse

import data.globalvar as globalvar
from data.data_pipeline import DataPipeline
from data.raw_input import UserInput
from utils.seed import setup_seed
from utils.module_loader import *
from config import *

from fairscale.nn.model_parallel.initialize import initialize_model_parallel


def run(config):
    result = []
    cnt = 1
    toolset = load_toolset(config.toolset)
    selector = load_selector(config.selector, toolset)
    data_pipeline = DataPipeline(toolset, selector, config.caller_root)
    for raw_input in UserInput(config.data.input).raw_inputs:
        print(f"processing {cnt}th question")
        cnt += 1
        data_pipeline.process_select(raw_input)
        if not config.pipeline_only:
            data_pipeline.process_call(raw_input)
            output = data_pipeline.process_result()
            result.append(
                {
                    "question": raw_input.values["question"],
                    "tool": data_pipeline.selection[1],
                    "category": data_pipeline.selection[0],
                    "output": output,
                }
            )
        else:
            result.append(
                {
                    "question": raw_input.values["question"],
                    "tool": data_pipeline.selection[1],
                    "category": data_pipeline.selection[0],
                }
            )
        print(f"finish processing {cnt}th question")

    output_dir = os.path.dirname(config.data.output)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    json.dump(result, open(config.data.output, "w"), indent=4)


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
    config.data.input = args.input
    config.data.output = args.output

    # Update config pipeline only
    config.pipeline_only = args.pipeline_only

    run(config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", action='store_true')
    parser.add_argument("--input", type=str, default="examples/inputs/saprot/saprot_input.json")
    parser.add_argument("--output", type=str, default="outputs/saprot_output.json")
    parser.add_argument("--pipeline_only", type=bool, default=False)
    args = parser.parse_args()
    main(args)
