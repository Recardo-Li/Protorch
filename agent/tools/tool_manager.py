import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import json
import sys
from typing import Any, Dict
ROOT_DIR = __file__.rsplit("/", 3)[0]
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import os
import yaml
from sentence_transformers import SentenceTransformer, util
from easydict import EasyDict
from agent.tools.register import get_tools


BASE_DIR = os.path.dirname(__file__)


import sys
import importlib


class ToolManager:
    def __init__(self, out_dir: str = None, enable_quick_run: bool = False):
        """
        Initialize the tool manager
        Args:
            out_dir: Output directory
            
            enable_quick_run: If True, the tool will run in quick mode if the config file has an example output
        """
        config_path = f"{BASE_DIR}/tool_manager_config.yaml"
        
        # Load config file
        with open(config_path, "r") as f:
            self.config = EasyDict(yaml.safe_load(f))
        
        # Load all available tools
        for tool_path in self.config.tools:
            module_name = f"agent.tools.{tool_path}"
            if module_name in sys.modules:
                del sys.modules[module_name]
            cmd = f"import {module_name}"
            exec(cmd)
        
        self.tools = {}
        # Instantiate all tools
        for tool in get_tools().values():
            obj = tool(enable_quick_run=enable_quick_run)
            if out_dir:
                obj.set_out_dir(out_dir)

            try:
                tool_name = obj.config.document.tool_name
            except Exception as e:
                print(f"Error: {e}")
                print(obj)
                raise
            self.tools[tool_name] = obj
    
    def __del__(self):
        """
        Destructor
        """
        for tool in self.tools.values():
            tool.terminate()
            del tool
        
        # if self.model exists, delete it
        if hasattr(self, "model"):
            del self.model
    
    def set_out_dir(self, out_dir: str):
        """
        Set the output directory
        """
        for tool in self.tools.values():
            tool.set_out_dir(out_dir)
        self.out_dir = out_dir
    
    def generate_tool_priority(self):
        return json.dumps(self.config.relationship, indent=4)
    
    def generate_argument_document(self, tool_name: str):
        """
        Generate the argument document for a tool
        Args:
            tool_name: Name of the tool
        """
        return self.tools[tool_name].get_argument_document()

    def generate_return_document(self, selected_tools: list = None):
        """
        Generate the return values for all available tools
        """
        document = ""
        for toolname in selected_tools:
            tool = self.get_tool(toolname)
            return_dict = {
                "tool_name": tool.config.document.tool_name,
                "tool_description": tool.config.document.tool_description,
                "return_values": tool.config.document.return_values,
            }
            document += json.dumps(return_dict, indent=4)
            document += "\n\n"

        return document

    def generate_document(self, selected_tools: list = None):
        """
        Generate the document for all available tools
        """
        document = ""
        for toolname in selected_tools:
            tool = self.get_tool(toolname)
            document += tool.get_document()
            document += "\n\n"
        
        return document
    
    def brief_documents(self, selected_tools):
        """
        Get brief documents for all tools
        """
        brief_docs = ""
        for toolname in selected_tools:
            tool = self.get_tool(toolname)
            brief_docs += f"{toolname}: {tool.config.document.tool_description}\n"
        return brief_docs
    
    def check_input(self, tool_name: str, tool_args: dict):
        """
        Check the input for a tool
        Args:
            tool_name: Name of the tool
            tool_args: Arguments for the tool
        """
        if tool_name not in self.tools.keys():
            return [f"Tool {tool_name} not found"]
        return self.tools[tool_name].check_input(tool_args)

    def call(self, tool_name: str, tool_args: dict):
        """
        Call a tool
        Args:
            tool_name: Name of the tool
            tool_args: Arguments for the tool
        """
        yield from self.tools[tool_name].mp_run(**tool_args)
    
    def quick_call(self, tool_name: str, tool_args: dict):
        """
        Call a tool quickly
        Args:
            tool_name: Name of the tool
            tool_args: Arguments for the tool
        """
        return self.tools[tool_name].quick_run(**tool_args)
    
    def get_tool(self, tool_name: str):
        """
        Get a tool by name
        Args:
            tool_name: Name of the tool
        """
        return self.tools[tool_name]
    
    def get_result(self, tool_name: str):
        """
        Get the result of a tool
        Args:
            tool_name: Name of the tool
        """
        return self.tools[tool_name].get_result()

    def standarize_json(self, doc_str: str):
        doc = json.loads(doc_str)
        standard_str = (
            (doc.get("category_name", "") or "")
            + ", "
            + (doc.get("tool_name", "") or "")
            + ", "
            + (doc.get("tool_description", "") or "")
            + ", required_params: "
            # + str(doc.get("required_parameters", ""))
            # + ", optional_params: "
            # + str(doc.get("optional_parameters", ""))
            # + ", return_values: "
            # + str(doc.get("return_values", ""))
        )
        return standard_str

    def initialize_retriever(self):
        """
        Initialize the retriever
        """
        self.corpus = {}
        self.corpus2tool = {}
        for tool in self.tools.values():
            standard_doc = self.standarize_json(tool.get_document())
            self.corpus[tool.config.document.tool_name] = standard_doc
            self.corpus2tool[standard_doc] = tool.config.document.tool_name
        corpus_ids = list(self.corpus.keys())
        self.corpus = [self.corpus[cid] for cid in corpus_ids]
        self.model = SentenceTransformer(f"{ROOT_DIR}/{self.config.embedding_model_path}")
        self.corpus_embeddings = self.model.encode(self.corpus, convert_to_tensor=True)
        
    def retrieve(self, query, top_k=10):
        """
        Retrieve tools
        Args:
            query: Query
            top_k: Number of tools to retrieve
        """
        if not hasattr(self, "model"):
            self.initialize_retriever()
        
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        hits = util.semantic_search(
            query_embedding,
            self.corpus_embeddings,
            top_k=top_k,
            score_function=util.cos_sim,
        )
        retrieved_tools = []
        for rank, hit in enumerate(hits[0]):
            tool_name = self.corpus2tool[self.corpus[hit["corpus_id"]]]
            retrieved_tools.append(tool_name)
        return retrieved_tools
        
        
if __name__ == '__main__':
    # Test
    tool_manager = ToolManager()
    tool_manager.initialize_retriever()
    print(tool_manager.retrieve("Predict the structure of ADSFDSFSEEWFAE"))
    del tool_manager
    tool_manager = ToolManager()
    tool_manager.initialize_retriever()
    print(tool_manager.retrieve("Predict the structure of ADSFDSFSEEWFAE"))