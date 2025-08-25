import sys
sys.path.append('.')

import yaml
import fire
import torch
from easydict import EasyDict
from utils.seed import setup_seed
from utils.module_loader import *
from fairscale.nn.model_parallel.initialize import initialize_model_parallel
from typing import Tuple

def setup_model_parallel():
    world_size = int(os.environ.get("WORLD_SIZE", -1))
    torch.distributed.init_process_group("nccl")
    initialize_model_parallel(world_size)

def run(config):
    # Setup model parallel
    setup_model_parallel()
    setup_seed(4)
    # Initialize a model
    toolset = load_toolset(config.toolset)
    selector = load_selector(config.selector, toolset)
    # model = load_selector(config.selector)

    if 0:
        for i, (name, param) in enumerate(selector.named_parameters()):
            print(f"{i}: {name}", param.requires_grad, id(param))
        return

    # Initialize a dataset
    data_module = load_dataset(config.dataset)

    # Initialize a trainer
    trainer = load_trainer(config)

    # Train and validate
    trainer.fit(model=selector, train_dataloaders=data_module._dataloader(stage="train", collate_fn=data_module.collate_func_fn))

    # Load best model and test performance
    selector.load_checkpoint(selector.save_path, load_prev_scheduler=selector.load_prev_scheduler)

    trainer.test(model=selector, dataloaders=data_module._dataloader(stage="test", collate_fn=data_module.collate_func_fn))


def main(config_file="config/uniprot.yaml"):
    with open(config_file, 'r', encoding='utf-8') as r:
        config = EasyDict(yaml.safe_load(r))

    if config.setting.seed:
        setup_seed(config.setting.seed)

    # set os environment variables
    for k, v in config.setting.os_environ.items():
        if v is not None and k not in os.environ:
            os.environ[k] = str(v)

        elif k in os.environ:
            # override the os environment variables
            config.setting.os_environ[k] = os.environ[k]

    # Only the root node will print the log
    if config.setting.os_environ.NODE_RANK != 0:
        config.Trainer.logger = False

    run(config)


if __name__ == '__main__':
    fire.Fire(main)