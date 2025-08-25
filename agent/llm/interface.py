import os
import yaml


now_cls = None


# register function as a wrapper for all models
def register_model(cls):
    global now_cls
    now_cls = cls
    return cls


def init_llm(model_py_path: str, **kwargs):
    """

    Args:
        model_py_path: Py file Path of model you want to use.
       **kwargs: Kwargs for model initialization

    Returns: Corresponding model
    """
    global now_cls
    
    sub_dirs = model_py_path.split(os.sep)
    cmd = f"from {'.' + '.'.join(sub_dirs[:-1])} import {sub_dirs[-1]}"
    exec(cmd)

    # Load meta template
    base_dir = os.path.dirname(__file__)
    template_path = f"{base_dir}/{os.path.dirname(model_py_path)}/meta_template.yaml"
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as r:
            meta_template = yaml.safe_load(r)

        kwargs["meta_template"] = meta_template
    
    return now_cls(**kwargs)