import shutil
import argparse
import time
from multiprocess import Process
import sys
import copy
import torch
import json

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from agent.tools.saprot_task.saprot.data_utils import make_config, check_column_label_and_stage
from agent.tools.saprot_task.saprot.model_interface import ModelInterface
from utils.module_loader import my_load_dataset, my_load_model, load_trainer

import os

def zip_folder(folder_path):
    abs_folder_path = os.path.abspath(folder_path)
    zip_path = abs_folder_path + ".zip"
    
    def process_folder():
        # 设置工作目录为当前文件夹
        temp_dir = os.path.dirname(abs_folder_path)
        os.chdir(temp_dir)
        
        # 打包文件夹为zip文件
        shutil.make_archive(zip_path.replace(".zip", ""), 'zip', abs_folder_path)
        print(f"Folder {abs_folder_path} has been zipped to {zip_path}")
        
    
    # 创建子进程
    process = Process(target=process_folder)
    process.start()
    process.join()
    
    return zip_path

def load_model(config):
    # initialize model
    model_config = copy.deepcopy(config)

    if "kwargs" in model_config.keys():
        kwargs = model_config.pop("kwargs")
    else:
        kwargs = {}

    model_config.update(kwargs)
    return ModelInterface.init_model(**model_config)

def tune(task_type, huggingface_path, dataset, default_config_path, save_path, batch_size="Adaptive", max_epoch=10, learning_rate=1e-3):
    config = make_config(batch_size=batch_size, max_epochs=max_epoch, learning_rate=learning_rate, base_model=huggingface_path, task_type=task_type, csv_dataset_path=dataset, default_config_path=default_config_path, save_path=save_path)
    data_module = my_load_dataset(config.dataset)
    print(f"Loaded dataset: {dataset[len(os.path.dirname(dataset))+1:]}")
    
    trainer = load_trainer(config)
    model = load_model(config.model)
    print(f"Loaded model: {model.model.__class__.__name__}")
    
    print(f"Actived LoRA model: {model.model.active_adapter}")
    trainable_parameters = model.model.print_trainable_parameters()
    print(f"{trainable_parameters}")

    trainer.fit(model=model, datamodule=data_module)  
    print(f"Training completed")
    
    
    # Load best model and test performance
    if model.save_path is not None:
        if config.model.kwargs.get("lora_kwargs", None):
            # Load LoRA model
            if len(getattr(config.model.kwargs.lora_kwargs, "config_list", [])) <= 1:
                config.model.kwargs.lora_kwargs.num_lora = 1
                config.model.kwargs.lora_kwargs.config_list = [
                    {"lora_config_path": model.save_path}
                ]
            # TODO: config.model not setted
            model = my_load_model(config.model)

        else:
            model.load_checkpoint(model.save_path)

        print(f"Loaded best model from: {model.save_path[len(os.path.dirname(dataset))+1:]}\nNow start testing")
        trainer.test(model=model, datamodule=data_module)
        
        print(f"Testing completed")

def check_valid_dataset(dataset):
    check_column_label_and_stage(dataset)
    return True

def main(args):
    task_type = args.task_type
    huggingface_path = args.huggingface_path
    dataset = args.dataset
    default_config_path = args.default_config_path
    batch_size = args.batch_size
    max_epoch = args.max_epoch
    learning_rate = args.learning_rate
    
    output_dir = os.path.dirname(dataset)
    cur_time = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    
    save_path = f"{output_dir}/{task_type}/{cur_time}/{os.path.splitext(os.path.basename(dataset))[0]}"
    
    assert check_valid_dataset(dataset), f"Invalid dataset: {dataset}"
    
    tune(task_type, huggingface_path, dataset, default_config_path, save_path, batch_size, max_epoch, learning_rate)
    
def get_args():
    parser = argparse.ArgumentParser(description="Tune a SaProt model")
    parser.add_argument("--task_type", type=str, required=True, help="Type of task")
    parser.add_argument("--huggingface_path", type=str, required=True, help="Path to huggingface model")
    parser.add_argument("--dataset", type=str, required=True, help="Path to dataset")
    parser.add_argument("--default_config_path", type=str, required=True, help="Path to default config")
    parser.add_argument("--batch_size", type=str, default="Adaptive", help="Batch size")
    parser.add_argument("--max_epoch", type=int, default=10, help="Max epoch")
    parser.add_argument("--learning_rate", type=float, default=1e-3, help="Learning rate")
    args = parser.parse_args()
    return args

def debug_get_args():
    parser = argparse.ArgumentParser(description="Tune a SaProt model")
    parser.add_argument("--task_type", type=str, default="classification", help="Type of task")
    parser.add_argument("--huggingface_path", type=str, default="/home/public/huggingface/SaProt/SaProt_35M_AF2", help="Path to huggingface model")
    parser.add_argument("--dataset", type=str, default="/root/ProtAgent/examples/saprot_train/[EXAMPLE][Classification-2Categories]Multiple_AA_Sequences.csv", help="Path to dataset")
    parser.add_argument("--default_config_path", type=str, default="/root/ProtAgent/agent/tools/saprot_task/saprot/default.yaml", help="Path to default config")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size")
    parser.add_argument("--max_epoch", type=int, default=10, help="Max epoch")
    parser.add_argument("--learning_rate", type=float, default=1e-3, help="Learning rate")
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    """
    EXAMPLE:
    python command.py   --task_type "classification" \
                    --huggingface_path "/home/public/huggingface/SaProt/SaProt_35M_AF2" \
                    --dataset "/root/ProtAgent/examples/saprot_train/[EXAMPLE][Classification-2Categories]Multiple_AA_Sequences.csv" \
                    --default_config_path "/root/ProtAgent/agent/tools/saprot_task/saprot/default.yaml" \
                    --batch_size 32 \
                    --max_epoch 10 \
                    --learning_rate 1e-3
                    
    python cmd.py   --task_type "pair_regression" \
                    --huggingface_path "/home/public/huggingface/SaProt/SaProt_35M_AF2" \
                    --dataset "/root/ProtAgent/examples/saprot_train/[EXAMPLE][Pair AA][Regression].csv" \
                    --default_config_path "/root/ProtAgent/agent/tools/saprot_task/saprot/default.yaml" \
                    --batch_size 32 \
                    --max_epoch 10 \
                    --learning_rate 1e-3
    """
    args = get_args()
    main(args)