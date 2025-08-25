import ast
import json


def standarize_internal_json(doc: json):
    if len(doc.get("name", "").split('.')) == 2:
        standard_str = (
        (doc.get("name", "").split('.')[0])
        + ", "
        + (doc.get("name", "").split('.')[1])
        + ", "
        )
    else: 
        standard_str = (
        (doc.get("name", "") or "")
        + ", "
        + (doc.get("name", "") or "")
        + ", "
        )
    standard_str += (
        (doc.get("description", "") or "")
        + " required_params: "
        + str(doc.get("parameters", ""))
    )
    # Replace single quotes with double quotes for JSON compatibility
    standard_str = standard_str.replace("'", '"')
    return standard_str

def standarize_external_doc(doc: str):
    # standard_str = doc+". If you call this tool, you must pass arguments in the JSON format {key: value}, where the key is the parameter name."
    # return standard_str
    return doc

def str2dict(input_str):
    if type(input_str) is dict:
        return input_str
    try:
        # Parse double quotes
        input_str = input_str.replace('"', '\"')
        result_dict = json.loads(f"{{{input_str}}}")
    except:
        # 添加大括号并替换单引号为双引号
        json_like_string = "{" + input_str.replace("'", '"') + "}"
        # 使用 ast.literal_eval 解析为字典
        result_dict = ast.literal_eval(json_like_string)
    
    return result_dict

