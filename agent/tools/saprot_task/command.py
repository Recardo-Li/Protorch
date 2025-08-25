from easydict import EasyDict
import sys
import torch
import argparse

ROOT_DIR = __file__.rsplit("/", 4)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from data.globalvar import *
from data.logger import logger_config
from agent.tools.saprot_task.saprot.model_interface import ModelInterface


sys.path.append(".")


class SaProtExecutor:
    def __init__(self, model_py_path, huggingface_path, lora_path, num_labels=None, label_dict=None):
        huggingface_path = huggingface_path
        if lora_path is None and num_labels is None:
            config = {"config_path": huggingface_path, "load_pretrained": True}
        elif lora_path is None and num_labels is not None:
            config = {
                "num_labels": num_labels,
                "config_path": huggingface_path,
                "load_pretrained": True
            }
        elif num_labels is not None:
            config = {
                "num_labels": num_labels,
                "config_path": huggingface_path,
                "load_pretrained": True,
                "lora_kwargs": EasyDict(
                    {
                        "is_trainable": True,
                        "num_lora": 1,
                        "config_list": [{"lora_config_path": lora_path}],
                    }
                ),
                "num_labels": num_labels
            }
        else:
            config = {
                "config_path": huggingface_path,
                "load_pretrained": True,
                "lora_kwargs": EasyDict(
                    {
                        "is_trainable": True,
                        "num_lora": 1,
                        "config_list": [{"lora_config_path": lora_path}],
                    }
                )
            }
        self.task_config = config
        print(f"Loading SaProt model {model_py_path}")
        self.model = ModelInterface.init_model(model_py_path, **config)
        print(f"Successfully Loaded {model_py_path}")

        self.tokenizer = self.model.tokenizer

        if torch.cuda.is_available():
            from .saprot.data_utils import select_best_gpu
            best_gpu_id = select_best_gpu()
            if isinstance(best_gpu_id, int):
                device = f"cuda:{best_gpu_id}"
            else:
                device = "cuda"
        else:
            device = "cpu"
            
        self.device = device 
        self.model.eval()
        self.model.to(device)
        
        self.label_dict = label_dict

    def get_executor(self, tool):
        if tool == "classification":
            return self.classification_inference
        elif tool == "regression":
            return self.regression_inference
        elif tool == "mutation":
            return self.mutation_inference
        elif tool == "pair_classification":
            return self.pair_inference
        elif tool == "pair_regression":
            return self.pair_inference
        elif tool == "token_classification":
            return self.token_classification_inference
        else:
            raise ValueError(f"Tool {tool} not found in SaProt tools")

    def token_classification_inference(self, sa_seq):
        inputs = self.tokenizer(sa_seq, return_tensors="pt")
        print(f"Suceessfully tokenized {sa_seq}")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        logits = self.model(inputs)
        preds = torch.argmax(logits, dim=-1).cpu().detach().numpy().tolist()
        if self.label_dict is not None:
            preds = ' '.join([f"{self.label_dict[pred]}({pred})" for pred in preds])
        print(f"Prediction complete. Result is {preds}")
        return preds

    def classification_inference(self, sa_seq):
        inputs = self.tokenizer(sa_seq, return_tensors="pt")
        print(f"Suceessfully tokenized {sa_seq}")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        logits = self.model(inputs)
        pred = torch.argmax(logits, dim=1).item()
        if self.label_dict is not None:
            pred = f"{self.label_dict[pred]}({pred})"
        print(f"Prediction complete. Result is {pred}")
        return pred

    def regression_inference(self, sa_seq):
        inputs = self.tokenizer(sa_seq, return_tensors="pt")
        print(f"Suceessfully tokenized {sa_seq}")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        logits = self.model(inputs)
        pred = logits.item()
        print(f"Prediction complete. Result is {pred}")
        return pred

    def mutation_inference(self, sa_seq, mut_info=None, mut_position=None):
        if mut_info is not None:
            print(f"Mutating {sa_seq} using mut_info({mut_info}) only")
            result = self.model.predict_mut(sa_seq, mut_info)
            print(f"Prediction complete. Result is {result}")
            return result
        else:
            print(f"Mutating {sa_seq} at position {mut_position}")
            result = self.model.predict_pos_prob(sa_seq, mut_position)
            print(f"Prediction complete. Result is {result}")

    def pair_inference(self, sa_seq1, sa_seq2):
        seq1 = "".join([char + "#" for char in sa_seq1])
        seq2 = "".join([char + "#" for char in sa_seq2])
        inputs1 = self.tokenizer(seq1, return_tensors="pt")
        inputs1 = {k: v.to(self.device) for k, v in inputs1.items()}
        print(f"Suceessfully tokenized {sa_seq1}")

        inputs2 = self.tokenizer(seq2, return_tensors="pt")
        inputs2 = {k: v.to(self.device) for k, v in inputs2.items()}
        print(f"Suceessfully tokenized {sa_seq2}")

        score = self.model(inputs1, inputs2).cpu().detach().numpy().tolist()
        if self.label_dict is not None:
            score = f"{self.label_dict[score]}({score})"
        print(f"Prediction complete. Result is {score}")
        return score

def main(args):
    model_py_path = args.model_py_path
    huggingface_path = args.huggingface_path
    lora_adaptor = args.lora_adaptor
    label_dict = args.label_dict
    num_labels = args.num_labels
    tool = model_py_path[7:-6]
    executor = SaProtExecutor(model_py_path, huggingface_path, lora_adaptor, num_labels, label_dict).get_executor(tool)
    if tool == "mutation":
        result = executor(args.sa_seq, args.mut_info, args.mut_position)
    elif tool == "pair_classification" or tool == "pair_regression":
        result = executor(args.sa_seq1, args.sa_seq2)
    else:
        result = executor(args.sa_seq)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_py_path", type=str, required=True)
    parser.add_argument("--huggingface_path", type=str, required=True)
    parser.add_argument("--lora_adaptor", type=str)
    parser.add_argument("--label_dict", type=dict)
    parser.add_argument("--num_labels", type=int)
    parser.add_argument("--tool", type=str)
    parser.add_argument("--sa_seq", type=str)
    parser.add_argument("--sa_seq1", type=str)
    parser.add_argument("--sa_seq2", type=str)
    parser.add_argument("--mut_info", type=str)
    parser.add_argument("--mut_position", type=int)
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    """
    EXAMPLE:
    python command.py   --model_py_path "saprot_classification_model" \
                    --huggingface_path "/home/public/huggingface/SaProt/SaProt_35M_AF2" \
                    --lora_adaptor "/home/public/huggingface/SaProt_Adapter/AVIDa-SARS-CoV-2-Alpha" \
                    --num_labels 2 \
                    --tool "classification" \
                    --sa_seq "A#A#A#A#A#A#A#"
                    
    python command.py   --model_py_path "saprot_mutation_model" \
                    --huggingface_path "/home/public/huggingface/SaProt/SaProt_35M_AF2" \
                    --tool "mutation" \
                    --sa_seq "A#A#A#A#A#A#A#" \
                    --mut_info A1E
                    
    python command.py   --model_py_path "saprot_classification_model" \
                    --huggingface_path "/home/public/huggingface/SaProt/SaProt_35M_AF2" \
                    --lora_adaptor "/root/ProtAgent/tmp/test/classification/2025-02-11_12:00:25/[EXAMPLE][Classification-2Categories]Multiple_AA_Sequences" \
                    --num_labels 2 \
                    --tool "classification" \
                    --sa_seq "A#A#A#A#A#A#A#"
    
    python command.py   --model_py_path 'saprot_pair_regression_model' \
                     --huggingface_path '/home/public/huggingface/SaProt/SaProt_35M_AF2' \
                     --lora_adaptor '/root/ProtAgent/tmp/test/pair_regression/2025-02-11_13:26:18/[EXAMPLE][Pair AA][Regression]' \
                     --sa_seq1 'A#A#A#A#A#A#A#A#A#A#' \
                     --sa_seq2 'A#A#A#A#A#A#A#A#A#A#'
                     
    python command.py --model_py_path saprot_token_classification_model --huggingface_path /home/public/huggingface/SaProt/SaProt_650M_AF2 --num_labels 2 --sa_seq A#A#A#A#A#A#A#A#A#A#
    """
    args = get_args()
    main(args)