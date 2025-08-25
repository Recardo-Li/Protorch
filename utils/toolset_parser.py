import re
import json
import os

from data.toolset import ToolSet


def standardize_category(category):
    save_category = category.replace(" ", "_").replace(",", "_").replace("/", "_")
    while " " in save_category or "," in save_category:
        save_category = save_category.replace(" ", "_").replace(",", "_")
    save_category = save_category.replace("__", "_")
    return save_category


def standardize(string):
    res = re.compile("[^\\u4e00-\\u9fa5^a-z^A-Z^0-9^_]")
    string = res.sub("_", string)
    string = re.sub(r"(_)\1+", "_", string).lower()
    while True:
        if len(string) == 0:
            return string
        if string[0] == "_":
            string = string[1:]
        else:
            break
    while True:
        if len(string) == 0:
            return string
        if string[-1] == "_":
            string = string[:-1]
        else:
            break
    if string[0].isdigit():
        string = "get_" + string
    return string


def change_name(name):
    change_list = ["from", "class", "return", "false", "true", "id", "and"]
    if name in change_list:
        name = "is_" + name
    return name

def standarize_json(doc: json):
    standard_str = (
        (doc.get("category_name", "") or "")
        + ", "
        + (doc.get("tool_name", "") or "")
        + ", "
        + (doc.get("tool_description", "") or "")
        + ", required_params: "
        + str(doc.get("required_parameters", ""))
        + ", optional_params: "
        + str(doc.get("optional_parameters", ""))
        + ", return_values: "
        + str(doc.get("return_values", ""))
        # + json.dumps(doc.get("required_parameters", ""))
        # + ", optional_params: "
        # + json.dumps(doc.get("optional_parameters", ""))
        # + ", return_values: "
        # + json.dumps(doc.get("return_values", ""))
    )
    return standard_str

def process_retrieval_document(toolset: ToolSet, mask=False, available_tools=None):
    ir_corpus = {}
    corpus2tool = {}
    for tool in os.listdir(toolset.doc_dir):
        if os.path.isdir(os.path.join(toolset.doc_dir, tool)):
            if mask and tool not in available_tools:
                continue
            tool_name = tool
            assert os.path.exists(
                os.path.join(toolset.doc_dir, tool_name)
            ), f"Document for {tool_name} not found"
            for func_name in toolset.tool_func_dict[tool_name].keys():
                doc_path = os.path.join(toolset.doc_dir, tool_name, f"{func_name}.json")
                with open(doc_path, 'r', encoding='UTF-8') as file:
                    doc = json.load(file)
                standard_str = standarize_json(doc)
                docid = f"{tool_name}_{func_name}"
                ir_corpus[docid] = standard_str
                corpus2tool[standard_str] = (
                    doc["category_name"],
                    doc["tool_name"],
                )
    return ir_corpus, corpus2tool
