import faiss
import numpy as np
import pandas as pd
import os
import yaml
import glob

from easydict import EasyDict
from data import globalvar
from utils.constants import sequence_level
from model.protrek.protrek_trimodal_model import ProTrekTrimodalModel
from tqdm import tqdm


def load_model(config):
    model_config = {
        "protein_config": glob.glob(f"{globalvar.huggingface_root/config.model_dir}/esm2_*")[0],
        "text_config": f"{globalvar.huggingface_root/config.model_dir}/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext",
        "structure_config": glob.glob(f"{globalvar.huggingface_root/config.model_dir}/foldseek_*")[0],
        "load_protein_pretrained": False,
        "load_text_pretrained": False,
        "from_checkpoint": glob.glob(f"{globalvar.huggingface_root/config.model_dir}/*.pt")[0],
    }

    model = ProTrekTrimodalModel(**model_config)
    model.eval()
    return model


def load_faiss_index(config, index_path: str):
    if config.faiss_config.IO_FLAG_MMAP:
        index = faiss.read_index(index_path, faiss.IO_FLAG_MMAP)
    else:
        index = faiss.read_index(index_path)

    index.metric_type = faiss.METRIC_INNER_PRODUCT
    return index


def load_index(config):
    all_index = {}

    # Load protein sequence index
    all_index["sequence"] = {}
    for db in tqdm(config.sequence_index_dir, desc="Loading sequence index..."):
        db_name = db["name"]
        index_dir = db["index_dir"]

        index_path = f"{globalvar.huggingface_root/index_dir}/sequence.index"
        sequence_index = load_faiss_index(config, index_path)

        id_path = f"{globalvar.huggingface_root/index_dir}/ids.tsv"
        uniprot_ids = pd.read_csv(id_path, sep="\t", header=None).values.flatten()

        all_index["sequence"][db_name] = {"index": sequence_index, "ids": uniprot_ids}

    # Load protein structure index
    # print("Loading structure index...")
    # all_index["structure"] = {}
    # for db in tqdm(config.structure_index_dir, desc="Loading structure index..."):
    #     db_name = db["name"]
    #     index_dir = db["index_dir"]

    #     index_path = f"{index_dir}/structure.index"
    #     structure_index = load_faiss_index(config, index_path)

    #     id_path = f"{index_dir}/ids.tsv"
    #     uniprot_ids = pd.read_csv(id_path, sep="\t", header=None).values.flatten()

    #     all_index["structure"][db_name] = {"index": structure_index, "ids": uniprot_ids}

    # Load text index
    all_index["text"] = {}
    valid_subsections = {}
    for db in tqdm(config.text_index_dir, desc="Loading text index..."):
        db_name = db["name"]
        index_dir = db["index_dir"]
        all_index["text"][db_name] = {}
        text_dir = f"{globalvar.huggingface_root/index_dir}/subsections"

        # Remove "Taxonomic lineage" from sequence_level. This is a special case which we don't need to index.
        valid_subsections[db_name] = set()
        sequence_level.add("Global")
        for subsection in tqdm(sequence_level):
            index_path = f"{globalvar.huggingface_root/text_dir}/{subsection.replace(' ', '_')}.index"
            if not os.path.exists(index_path):
                continue

            text_index = load_faiss_index(config, index_path)

            id_path = f"{globalvar.huggingface_root/text_dir}/{subsection.replace(' ', '_')}_ids.tsv"
            text_ids = pd.read_csv(id_path, sep="\t", header=None).values.flatten()

            all_index["text"][db_name][subsection] = {
                "index": text_index,
                "ids": text_ids,
            }
            valid_subsections[db_name].add(subsection)

    # Sort valid_subsections
    for db_name in valid_subsections:
        valid_subsections[db_name] = sorted(list(valid_subsections[db_name]))

    return all_index, valid_subsections


def load(logger=None):
    # Load the config file
    config_path = f"funchub/func_impl/protrek/config.yaml"
    with open(config_path, "r", encoding="utf-8") as r:
        config = EasyDict(yaml.safe_load(r))

    device = "cuda"

    if logger is not None:
        logger.info("Loading model...")
    model = load_model(config)
    model.to(device)

    if logger is not None:
        logger.info("Loading index...")
    all_index, valid_subsections = load_index(config)
    if logger is not None:
        logger.info("Done...")
    return model, all_index, valid_subsections


def protrek_protein2text(protein_sequence: str, database: str, subsection: str, logger=None) -> str:
    """
    Get text description for a protein sequence
    Args:
        protein_sequence: A string representing the amino acid sequence of the protein.

        database: The specific database to search for the protein description, e.g. 'UniProt'.

        subsection: The specific subsection of the database to search for the protein description, e.g. 'Function'.

    Returns:
        The text description of the protein.
    """

    model, all_index, valid_subsections = load(logger)

    protein_repr = model.get_protein_repr([protein_sequence]).detach().cpu().numpy()
    index = all_index["text"][database][subsection]["index"]
    ids = all_index["text"][database][subsection]["ids"]

    # Retrieve The top 1 text description
    scores, ranks = index.search(protein_repr, 1)
    scores, ranks = scores[0], ranks[0]
    text = ids[ranks[0]]

    return text


def protrek_text2protein(text: str, database: str, logger=None) -> str:
    """
    Get protein sequence for a text description
    Args:
        text: The natural language text description of a protein."

        database: The specific database to search for the protein description, e.g. 'UniProt'.

    Returns:
        The protein sequence.
    """

    model, all_index, valid_subsections = load(logger)

    text_repr = model.get_text_repr([text]).detach().cpu().numpy()
    index = all_index["sequence"][database]["index"]
    ids = all_index["sequence"][database]["ids"]

    # Retrieve The top 1 text description
    scores, ranks = index.search(text_repr, 1)
    scores, ranks = scores[0], ranks[0]
    seq = ids[ranks[0]]

    return seq
