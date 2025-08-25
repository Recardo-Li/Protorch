import os
import sys

sys.path.append(".")

from data.toolset import ToolSet

new_doc_dir = "tmp"
toolset = ToolSet("funchub")

for category in os.listdir(new_doc_dir):
    for doc in os.listdir(os.path.join(new_doc_dir, category)):
        doc_path = os.path.join(new_doc_dir, category, doc)
        func_name = os.path.splitext(doc)[0]
        toolset.add_func(doc_path, func_name, category)
