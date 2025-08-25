from easydict import EasyDict
import sys
import torch

from data.globalvar import *
from data.logger import logger_config
from model.model_interface import ModelInterface


sys.path.append(".")


class SaProtExecutor:
    def __init__(self, model_py_path, huggingface_path, lora_path, log_path, num_labels=None):
        self.logger = logger_config("SaProtExecutor", file_path=log_path)
        huggingface_path = huggingface_path
        if lora_path is None:
            config = {"config_path": huggingface_path, "load_pretrained": True}
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
        self.logger.info(f"Loading SaProt model {model_py_path} from {huggingface_path}")
        self.model = ModelInterface.init_model(model_py_path, **config)
        self.logger.info(f"Successfully Loaded {model_py_path}")

        self.tokenizer = self.model.tokenizer

        device = "cuda"
        self.model.eval()
        self.model.to(device)

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

    def token_classification_inference(self, aa_seq):
        seq = "".join([char + "#" for char in aa_seq])
        inputs = self.tokenizer(seq, return_tensors="pt")
        self.logger.info(f"Suceessfully tokenized {aa_seq}")
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
        logits = self.model(inputs)
        preds = torch.argmax(logits, dim=-1)
        self.logger.info(f"Prediction complete. Result is {preds}")
        return preds

    def classification_inference(self, aa_seq):
        seq = "".join([char + "#" for char in aa_seq])
        inputs = self.tokenizer(seq, return_tensors="pt")
        self.logger.info(f"Suceessfully tokenized {aa_seq}")
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
        logits = self.model(inputs)
        pred = torch.argmax(logits, dim=1)
        self.logger.info(f"Prediction complete. Result is {pred}")
        return pred

    def regression_inference(self, aa_seq):
        seq = "".join([char + "#" for char in aa_seq])
        inputs = self.tokenizer(seq, return_tensors="pt")
        self.logger.info(f"Suceessfully tokenized {aa_seq}")
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
        logits = self.model(inputs)
        pred = logits
        self.logger.info(f"Prediction complete. Result is {pred}")
        return pred

    def mutation_inference(self, aa_seq, mut_info=None, mut_position=None):
        seq = "".join([char + "#" for char in aa_seq])
        if mut_info is not None:
            self.logger.info(f"Mutating {aa_seq} using mut_info({mut_info}) only")
            return self.model.predict_mut(seq, mut_info)
        else:
            self.logger.info(f"Mutating {aa_seq} at position {mut_position}")
            return self.model.predict_pos_prob(seq, mut_position)

    def pair_inference(self, aa_seq1, aa_seq2):
        seq1 = "".join([char + "#" for char in aa_seq1])
        seq2 = "".join([char + "#" for char in aa_seq2])
        inputs1 = self.tokenizer(seq1, return_tensors="pt")
        inputs1 = {k: v.to("cuda") for k, v in inputs1.items()}
        self.logger.info(f"Suceessfully tokenized {aa_seq1}")

        inputs2 = self.tokenizer(seq2, return_tensors="pt")
        inputs2 = {k: v.to("cuda") for k, v in inputs2.items()}
        self.logger.info(f"Suceessfully tokenized {aa_seq2}")

        score = self.model(inputs1, inputs2)
        self.logger.info(f"Prediction complete. Result is {score}")
        return score
