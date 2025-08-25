import os
import json

template = """{
    "category_name": "saprot_tune",
    "tool_name": "<toolname>",
    "tool_description": "",
    "required_parameters": [
        {
            "name": "dataset",
            "type": "TEXT",
            "description": "Training dataset of <toolname> model. Dataset should be a .csv file with three required columns: sequence, label and stage"
        },
        {
            "name": "base_model",
            "type": "TEXT",
            "description": "Base model for <toolname> model. Base model should be one of (1) Official pretrained SaProt (35M) (2) Official pretrained SaProt (650M)"
        }
    ],
    "optional_parameters": [
        {
            "name": "batch_size",
            "type": "PARAMETER",
            "description": "batch_size depends on the number of training samples. Adaptive (default choice) refers to automatic batch size according to your data size. If your training data set is large enough, you can use 32, 64, 128, 256, ..., others can be set to 8, 4, 2.",
            "default": "Adaptive"
        },
        {
            "name": "max_epoch",
            "type": "PARAMETER",
            "description": "max_epochs refers to the maximum number of training iterations. A larger value needs more training time. The best model will be saved after each iteration. You can adjust max_epochs to control training duration.",
            "default": "1"
        },
        {
            "name": "learning_rate",
            "type": "PARAMETER",
            "description": "learning_rate affects the convergence speed of the model. Through experimentation, we have found that 5.0e-4 is a good default value for base model Official pretrained SaProt (650M) and 1.0e-3 for Official pretrained SaProt (35M).",
            "default": "1e-3"
        }
    ],
    "return_values": [
        {
            "name": "status",
            "type": "TEXT",
            "description": "Whether the model is successfully trained or not"
        }
    ]
}
"""

tool_dict = json.load(open("tmp/saprot_tune.json"))
if not os.path.exists("tmp/saprot_tune"):
    os.makedirs("tmp/saprot_tune")

for name in tool_dict.keys():
    path = os.path.join("tmp/saprot_tune", f"{name}.json")
    subsection = str(name).split(".")[0]
    content = template.replace("<toolname>", subsection)
    with open(path, "w") as fp:
        fp.write(content)
