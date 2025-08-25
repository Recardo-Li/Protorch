import os
import yaml
from easydict import EasyDict

def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as r:
        config = EasyDict(yaml.safe_load(r))
    return config

cfg_inference_local = load_config('config/inference_local.yaml')
cfg_inference_public = load_config('config/inference_public.yaml')
