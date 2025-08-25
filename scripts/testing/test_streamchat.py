import sys

sys.path.append("/root/ProtAgent")
import yaml

from pathlib import Path
import data.globalvar as globalvar
from data.data_pipeline import DataPipeline

from agent.agent.protein_react_guidance import ProteinReActAgent

from agent.action import *
from agent.action.chat_action import ChatAction
from agent.action.python_interpreter import PythonInterpreter
from agent.action.fasta import FastaOperator
from agent.action import ActionExecutor

from lagent.schema import AgentStatusCode


from easydict import EasyDict

from utils.module_loader import load_selector, load_toolset




config_path = "config/inference_public.yaml"
with open(config_path, 'r', encoding='utf-8') as r:
    config = EasyDict(yaml.safe_load(r))

if config.data_dir:
    globalvar.huggingface_root = Path(config.data_dir.huggingface_root)
    globalvar.bin_root = Path(config.data_dir.bin_root)
    globalvar.modelhub_root = Path(config.data_dir.modelhub_root)
    globalvar.dataset_root = Path(config.data_dir.dataset_root)
else:
    # set to local folder by default
    globalvar.huggingface_root = Path("huggingface")
    globalvar.bin_root = Path("bin")
    globalvar.modelhub_root = Path("modelhub")
    globalvar.dataset_root = Path("dataset")


toolset = load_toolset(config.toolset)
selector = load_selector(config.selector, toolset)
data_pipeline = DataPipeline(toolset, selector, config.caller_root)

chatbot = ProteinReActAgent(
    model_path=config.agent.path,
    python_interpreter=None,
    datapipeline=data_pipeline,
    action_executor=None,
    max_turn=10
)

# chatbot = ReActAgent(
#     model_path=config.agent.path,
#     action_executor=None,
#     max_turn=10
# )


action_executor = ActionExecutor(actions=[
    # get_tool("ArxivSearch"),
    ChatAction(),
    FastaOperator(),
    PythonInterpreter(),
])  # noqa: F841

chatbot.action_executor = action_executor
chatbot.max_turn = 10

messages = [
    # {"role": "user", "content": "?"},
    # {"role": "user", "content": "Tell me something about saprot."},
    # {"role": "user", "content": "Write me a 3-line poem with evey line containing 5 words."},
    # {"role": "user", "content": "I have uploaded several files: /tmp/gradio/9fc6da0c52f1f14d9edd055c3d7660d7f20763c97af56b1329b3f9bef919eb5e/AF-A5VJA0-F1-model_v4.pdb."},
    # {"role": "user", "content": "You have to write a program to compute how many 'r's in the word 'strawberry'"},
    # {"role": "user", "content": "write a program to return the square value of the 0.6846."},
    # {"role": "user", "content": "Obtain the protein sequence 'A0PK11' and 'A6NI61' separately in UniProt. Use ESMFold to predict their structures, and calculate the TM-score. Finally write a program to return the square value of the TM-score."},
    # {"role": "user", "content": "Fetch the sequence and structure of 'A0PK11'. Predict the structure given the sequnece using ESMFold, and then calculate the TM-score between the predicted structure and the real structure. Finally return the square value of this score."},
    # {"role": "user", "content": "Predict the structure of sequence 'AARAAAAAAAARARARARAA'"},
    # {"role": "user", "content": "Find me the authors of 'Exploring evolution-aware &-free protein language models as protein function predictors'"},
    {"role": "user", "content": "Use Saprot to predict the mutation of sequence 'AARAAAAAAAARARARARAA'"},
]

available_types = ['Function', 'Structure', 'Design', 'Interaction', 'Search', 'Align', 'Annotation']
available_tools = ['saprot_regression', 'saprot_mutation', 'saprot_pair_regression', 'saprot_pair_classification', 'saprot_classification', 'saprot_token_classification', 'saprot_pair_classification', 'saprot_tune_regression', 'saprot_tune_pair_regression', 'saprot_tune_classification', 'saprot_tune_token_classification', 'saprot_tune_pair_classification', 'alphafold2', 'esmfold', 'rf_diffusion_binder_design', 'rf_diffusion_motif_scaffolding', 'rf_diffusion_partial_diffusion', 'rf_diffusion_unconditional_protein_design', 'proteinmpnn', 'pinal', 'deepab', 'diffab_antigen_antibody', 'diffab_antigen_only', 'umol', 'blast', 'mmseqs_cluster', 'mmseqs_group', 'mmseqs_search', 'protrek_protein2text', 'protrek_text2protein', 'foldseek', 'uniprot_fetch_sequence', 'uniprot_fetch_structure', 'uniprot_qa', 'wikipedia', 'pfam_entry', 'pfam_match', 'biorxiv', 'pubmed', 'clustalw', 'tmalign', 'hmm_build', 'hmm_search']
start_tool_name = None
retrieval_results = [{'category': 'pinal', 'tool_name': 'pinal'}, {'category': 'saprot_token_classification', 'tool_name': 'saprot_token_classification'}, {'category': 'saprot_tune', 'tool_name': 'saprot_tune_token_classification'}, {'category': 'saprot_classification', 'tool_name': 'saprot_classification'}, {'category': 'uniprot', 'tool_name': 'uniprot_fetch_sequence'}]


# chatbot.stream_chat(messages)
lm = chatbot.stream_chat(messages, action_executor, available_types, available_tools, start_tool_name, retrieval_results)
current_length = 0
for agent_return in lm:
    print(agent_return.content[current_length:], end='', flush=True)
    current_length = len(agent_return.content)
    
    if agent_return.state == AgentStatusCode.PLUGIN_START:
        chatbot.modify_response("No ")
        break

# part["thought"]