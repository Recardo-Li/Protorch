import os
import yaml
import glob

def register_model(cls):
    global now_cls
    global now_model_py_path
    now_cls[now_model_py_path] = cls
    return cls

now_cls = {}
now_model_py_path = None


class ModelInterface:
    @classmethod
    def init_model(cls, model_py_path: str, **kwargs):
        """
        Args:
            model_py_path: Py file Path of model you want to use.
           **kwargs: Kwargs for model initialization

        Returns: Corresponding model
        """
        global now_model_py_path
        now_model_py_path = model_py_path
        sub_dirs = model_py_path.split(os.sep)
        cmd = f"from {'.' + '.'.join(sub_dirs[:-1])} import {sub_dirs[-1]}"
        print(cmd)
        exec(cmd)

        return now_cls[now_model_py_path](**kwargs)