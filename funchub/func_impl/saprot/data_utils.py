import pandas as pd
import os
import time

from pathlib import Path
from huggingface_hub import snapshot_download
from agent.action.config import get_temp_dir
from utils.mpr import MultipleProcessRunnerSimplifier
from utils.foldseek_util import get_struc_seq
import os
import torch
import lmdb
import yaml
import copy

from easydict import EasyDict
from utils.construct_lmdb import construct_lmdb

LMDB_HOME = Path("tmp/lmdb")
DATASET_HOME = Path("tmp/SaProt_Dataset")
STRUCTURE_HOME = Path("tmp/structure")
FOLDSEEK_PATH = Path("")


num_workers = 2
val_check_interval = 0.5
limit_train_batches = 1.0
limit_val_batches = 1.0
limit_test_batches = 1.0



aa_set = {
    "A",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "K",
    "L",
    "M",
    "N",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "V",
    "W",
    "Y",
}
foldseek_struc_vocab = "pynwrqhgdlvtmfsaeikc#"

data_type_list = [
    "Single AA Sequence",
    "Single SA Sequence",
    "Single UniProt ID",
    "Single PDB/CIF Structure",
    "Multiple AA Sequences",
    "Multiple SA Sequences",
    "Multiple UniProt IDs",
    "Multiple PDB/CIF Structures",
    "SaprotHub Dataset",
    "A pair of AA Sequences",
    "A pair of SA Sequences",
    "A pair of UniProt IDs",
    "A pair of PDB/CIF Structures",
    "Multiple pairs of AA Sequences",
    "Multiple pairs of SA Sequences",
    "Multiple pairs of UniProt IDs",
    "Multiple pairs of PDB/CIF Structures",
]

data_type_list_single = [
    "Single AA Sequence",
    "Single SA Sequence",
    "Single UniProt ID",
    "Single PDB/CIF Structure",
    "A pair of AA Sequences",
    "A pair of SA Sequences",
    "A pair of UniProt IDs",
    "A pair of PDB/CIF Structures",
]

data_type_list_multiple = [
    "Multiple AA Sequences",
    "Multiple SA Sequences",
    "Multiple UniProt IDs",
    "Multiple PDB/CIF Structures",
    "Multiple pairs of AA Sequences",
    "Multiple pairs of SA Sequences",
    "Multiple pairs of UniProt IDs",
    "Multiple pairs of PDB/CIF Structures",
]

task_type_dict = {
    "Protein-level Classification": "classification",
    "Residue-level Classification": "token_classification",
    "Protein-level Regression": "regression",
    "Protein-protein Classification": "pair_classification",
    "Protein-protein Regression": "pair_regression",
}
model_type_dict = {
    "classification": "saprot/saprot_classification_model",
    "token_classification": "saprot/saprot_token_classification_model",
    "regression": "saprot/saprot_regression_model",
    "pair_classification": "saprot/saprot_pair_classification_model",
    "pair_regression": "saprot/saprot_pair_regression_model",
}
dataset_type_dict = {
    "classification": "saprot/saprot_classification_dataset",
    "token_classification": "saprot/saprot_token_classification_dataset",
    "regression": "saprot/saprot_regression_dataset",
    "pair_classification": "saprot/saprot_pair_classification_dataset",
    "pair_regression": "saprot/saprot_pair_regression_dataset",
}
training_data_type_dict = {
    "Single AA Sequence": "AA",
    "Single SA Sequence": "SA",
    "Single UniProt ID": "SA",
    "Single PDB/CIF Structure": "SA",
    "Multiple AA Sequences": "AA",
    "Multiple SA Sequences": "SA",
    "Multiple UniProt IDs": "SA",
    "Multiple PDB/CIF Structures": "SA",
    "SaprotHub Dataset": "SA",
    "A pair of AA Sequences": "AA",
    "A pair of SA Sequences": "SA",
    "A pair of UniProt IDs": "SA",
    "A pair of PDB/CIF Structures": "SA",
    "Multiple pairs of AA Sequences": "AA",
    "Multiple pairs of SA Sequences": "SA",
    "Multiple pairs of UniProt IDs": "SA",
    "Multiple pairs of PDB/CIF Structures": "SA",
}


class font:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"

    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    RESET = "\033[0m"


def read_csv_dataset(uploaded_csv_path):
    df = pd.read_csv(uploaded_csv_path)
    df.columns = df.columns.str.lower()
    return df

def get_num_labels(csv_dataset_path):
    check_column_label_and_stage(csv_dataset_path)
    df = read_csv_dataset(csv_dataset_path)
    return len(df["label"].unique())

def check_column_label_and_stage(csv_dataset_path):
    df = read_csv_dataset(csv_dataset_path)
    assert {"label", "stage"}.issubset(
        df.columns
    ), f"Make sure your CSV dataset includes both `label` and `stage` columns!\nCurrent columns: {df.columns}"
    column_values = set(df["stage"].unique())
    assert all(
        value in column_values for value in ["train", "valid", "test"]
    ), f"Ensure your dataset includes samples for all three stages: `train`, `valid` and `test`.\nCurrent columns: {df.columns}"


def get_data_type(csv_dataset_path):
    # AA, SA, Pair AA, Pair SA
    df = read_csv_dataset(csv_dataset_path)

    # AA, SA
    if "sequence" in df.columns:
        second_token = df.loc[0, "sequence"][1]
        if second_token in aa_set:
            return "Multiple AA Sequences"
        elif second_token in foldseek_struc_vocab:
            return "Multiple SA Sequences"
        else:
            raise RuntimeError(
                f"The sequence in the dataset({csv_dataset_path}) are neither SA Sequences nor AA Sequences. Please check carefully."
            )

    # Pair AA, Pair SA
    elif "sequence_1" in df.columns and "sequence_2" in df.columns:
        second_token = df.loc[0, "sequence_1"][1]
        if second_token in aa_set:
            return "Multiple pairs of AA Sequences"
        elif second_token in foldseek_struc_vocab:
            return "Multiple pairs of SA Sequences"
        else:
            raise RuntimeError(
                f"The sequence in the dataset({csv_dataset_path}) are neither SA Sequences nor AA Sequences. Please check carefully."
            )

    else:
        raise RuntimeError(
            f"The data type of the dataset({csv_dataset_path}) should be one of the following types: Multiple AA Sequences, Multiple SA Sequences, Multiple pairs of AA Sequences, Multiple pairs of SA Sequences"
        )


def check_task_type_and_data_type(original_task_type, data_type):
    if "pair" in original_task_type:
        assert (
            data_type == "SaprotHub Dataset" or "pair" in data_type
        ), f"The current `data_type`({data_type}) is incompatible with the current `task_type`({original_task_type}). Please use Pair Sequence Datset for {original_task_type} task!"
    else:
        assert (
            "pair" not in data_type
        ), f"The current `data_type`({data_type}) is incompatible with the current `task_type`({original_task_type}). Please avoid using the Pair Sequence Dataset({data_type}) for the {original_task_type} task!"


def get_SA_sequence_by_data_type(data_type, raw_data):

    # Multiple sequences
    # raw_data = upload_files/xxx.csv

    # 8. SaprotHub Dataset
    if data_type == "SaprotHub Dataset":
        input_repo_id = raw_data
        REPO_ID = input_repo_id.value

        if REPO_ID.startswith("/"):
            return Path(REPO_ID)

        snapshot_download(
            repo_id=REPO_ID, repo_type="dataset", local_dir=DATASET_HOME / REPO_ID
        )
        csv_dataset_path = DATASET_HOME / REPO_ID / "dataset.csv"
        assert csv_dataset_path.exists(), f"Can't find {csv_dataset_path}"
        protein_df = read_csv_dataset(csv_dataset_path)

        data_type = get_data_type(csv_dataset_path)

        return get_SA_sequence_by_data_type(data_type, csv_dataset_path)

    elif data_type in data_type_list_multiple:
        uploaded_csv_path = raw_data
        csv_dataset_path = DATASET_HOME / os.path.basename(uploaded_csv_path)
        if not os.path.exists(DATASET_HOME):
            os.makedirs(DATASET_HOME)
        protein_df = read_csv_dataset(uploaded_csv_path)

        if "pair" in data_type:
            assert {"sequence_1", "sequence_2"}.issubset(
                protein_df.columns
            ), f"The CSV dataset ({uploaded_csv_path}) must contain `sequence_1` and `sequence_2` columns. \n Current columns:{protein_df.columns}"
        else:
            assert (
                "sequence" in protein_df.columns
            ), f"The CSV Dataset({uploaded_csv_path}) must contain a `sequence` column. \n Current columns:{protein_df.columns}"

        # 4. Multiple AA Sequences
        if data_type == "Multiple AA Sequences":
            for index, value in protein_df["sequence"].items():
                sa_seq = ""
                for aa in value:
                    sa_seq += aa + "#"
                protein_df.at[index, "sequence"] = sa_seq

            protein_df.to_csv(csv_dataset_path, index=None)
            return csv_dataset_path

        # 5. Multiple SA Sequences
        elif data_type == "Multiple SA Sequences":
            protein_df.to_csv(csv_dataset_path, index=None)
            return csv_dataset_path

        # 6. Multiple UniProt IDs
        elif data_type == "Multiple UniProt IDs":
            protein_list = protein_df.iloc[:, "sequence"].tolist()
            uniprot2pdb(protein_list)
            protein_list = [(uniprot_id, "AF2", "A") for uniprot_id in protein_list]
            mprs = MultipleProcessRunnerSimplifier(
                protein_list, pdb2sequence, n_process=2, return_results=True
            )
            outputs = mprs.run()

            protein_df["sequence"] = [output.split("\t")[1] for output in outputs]
            protein_df.to_csv(csv_dataset_path, index=None)
            return csv_dataset_path

        # 7. Multiple PDB/CIF Structures
        elif data_type == "Multiple PDB/CIF Structures":
            # protein_list = [(uniprot_id, type, chain), ...]
            # protein_list = [item.split('.')[0] for item in protein_df.iloc[:, 0].tolist()]
            # uniprot2pdb(protein_list)
            protein_list = []
            for row_tuple in protein_df.itertuples(index=False):
                assert row_tuple.type in [
                    "PDB",
                    "AF2",
                ], 'The type of structure must be either "PDB" or "AF2"!'
                protein_list.append(row_tuple)
            mprs = MultipleProcessRunnerSimplifier(
                protein_list, pdb2sequence, n_process=2, return_results=True
            )
            outputs = mprs.run()

            protein_df["sequence"] = [output.split("\t")[1] for output in outputs]
            protein_df.to_csv(csv_dataset_path, index=None)
            return csv_dataset_path

        # 13. Pair Multiple AA Sequences
        elif data_type == "Multiple pairs of AA Sequences":
            for i in ["1", "2"]:
                for index, value in protein_df[f"sequence_{i}"].items():
                    sa_seq = ""
                    for aa in value:
                        sa_seq += aa + "#"
                    protein_df.at[index, f"sequence_{i}"] = sa_seq

                protein_df[f"name_{i}"] = f"name_{i}"
                protein_df[f"chain_{i}"] = "A"

            protein_df.to_csv(csv_dataset_path, index=None)
            return csv_dataset_path

        # 14. Pair Multiple SA Sequences
        elif data_type == "Multiple pairs of SA Sequences":
            for i in ["1", "2"]:
                protein_df[f"name_{i}"] = f"name_{i}"
                protein_df[f"chain_{i}"] = "A"

            protein_df.to_csv(csv_dataset_path, index=None)
            return csv_dataset_path

        # 15. Pair Multiple UniProt IDs
        elif data_type == "Multiple pairs of UniProt IDs":
            for i in ["1", "2"]:
                protein_list = protein_df.loc[:, f"sequence_{i}"].tolist()
                uniprot2pdb(protein_list)
                protein_df[f"name_{i}"] = protein_list
                protein_list = [(uniprot_id, "AF2", "A") for uniprot_id in protein_list]
                mprs = MultipleProcessRunnerSimplifier(
                    protein_list, pdb2sequence, n_process=2, return_results=True
                )
                outputs = mprs.run()

                protein_df[f"sequence_{i}"] = [
                    output.split("\t")[1] for output in outputs
                ]
                protein_df[f"chain_{i}"] = "A"

            protein_df.to_csv(csv_dataset_path, index=None)
            return csv_dataset_path

        elif data_type == "Multiple pairs of PDB/CIF Structures":
            # columns: sequence_1, sequence_2, type_1, type_2, chain_1, chain_2, label, stage

            # protein_list = [(uniprot_id, type, chain), ...]
            # protein_list = [item.split('.')[0] for item in protein_df.iloc[:, 0].tolist()]
            # uniprot2pdb(protein_list)

            for i in ["1", "2"]:
                protein_list = []
                for index, row in protein_df.iterrows():
                    assert row[f"type_{i}"] in [
                        "PDB",
                        "AF2",
                    ], 'The type of structure must be either "PDB" or "AF2"!'
                    row_tuple = (
                        row[f"sequence_{i}"],
                        row[f"type_{i}"],
                        row[f"chain_{i}"],
                    )
                    protein_list.append(row_tuple)
                mprs = MultipleProcessRunnerSimplifier(
                    protein_list, pdb2sequence, n_process=2, return_results=True
                )
                outputs = mprs.run()

                # add name column, del type column
                protein_df[f"name_{i}"] = protein_df[f"sequence_{i}"].apply(
                    lambda x: x.split(".")[0]
                )
                protein_df.drop(f"type_{i}", axis=1, inplace=True)
                protein_df[f"sequence_{i}"] = [
                    output.split("\t")[1] for output in outputs
                ]

            # columns: name_1, name_2, chain_1, chain_2, sequence_1, sequence_2, label, stage
            protein_df.to_csv(csv_dataset_path, index=None)
            return csv_dataset_path

    else:
        # 0. Single AA Sequence
        if data_type == "Single AA Sequence":
            input_seq = raw_data
            aa_seq = input_seq.value

            sa_seq = ""
            for aa in aa_seq:
                sa_seq += aa + "#"
            return sa_seq

        # 1. Single SA Sequence
        elif data_type == "Single SA Sequence":
            input_seq = raw_data
            sa_seq = input_seq.value

            return sa_seq

        # 2. Single UniProt ID
        elif data_type == "Single UniProt ID":
            input_seq = raw_data
            uniprot_id = input_seq.value

            protein_list = [(uniprot_id, "AF2", "A")]
            uniprot2pdb([protein_list[0][0]])
            mprs = MultipleProcessRunnerSimplifier(
                protein_list, pdb2sequence, n_process=2, return_results=True
            )
            seqs = mprs.run()
            sa_seq = seqs[0].split("\t")[1]
            return sa_seq

        # 3. Single PDB/CIF Structure
        elif data_type == "Single PDB/CIF Structure":
            uniprot_id = raw_data[0]
            struc_type = raw_data[1].value
            chain = raw_data[2].value

            protein_list = [(uniprot_id, struc_type, chain)]
            mprs = MultipleProcessRunnerSimplifier(
                protein_list, pdb2sequence, n_process=2, return_results=True
            )
            seqs = mprs.run()
            assert (
                len(seqs) > 0
            ), "Unable to convert to SA sequence. Please check the `type`, `chain`, and `.pdb/.cif file`."
            sa_seq = seqs[0].split("\t")[1]
            return sa_seq

        # 9. Pair Single AA Sequences
        elif data_type == "A pair of AA Sequences":
            input_seq_1, input_seq_2 = raw_data
            sa_seq1 = get_SA_sequence_by_data_type("Single AA Sequence", input_seq_1)
            sa_seq2 = get_SA_sequence_by_data_type("Single AA Sequence", input_seq_2)

            return (sa_seq1, sa_seq2)

        # 10. Pair Single SA Sequences
        elif data_type == "A pair of SA Sequences":
            input_seq_1, input_seq_2 = raw_data
            sa_seq1 = get_SA_sequence_by_data_type("Single SA Sequence", input_seq_1)
            sa_seq2 = get_SA_sequence_by_data_type("Single SA Sequence", input_seq_2)

            return (sa_seq1, sa_seq2)

        # 11. Pair Single UniProt IDs
        elif data_type == "A pair of UniProt IDs":
            input_seq_1, input_seq_2 = raw_data
            sa_seq1 = get_SA_sequence_by_data_type("Single UniProt ID", input_seq_1)
            sa_seq2 = get_SA_sequence_by_data_type("Single UniProt ID", input_seq_2)

            return (sa_seq1, sa_seq2)

        # 12. Pair Single PDB/CIF Structure
        elif data_type == "A pair of PDB/CIF Structures":
            uniprot_id1 = raw_data[0]
            struc_type1 = raw_data[1].value
            chain1 = raw_data[2].value

            protein_list1 = [(uniprot_id1, struc_type1, chain1)]
            mprs1 = MultipleProcessRunnerSimplifier(
                protein_list1, pdb2sequence, n_process=2, return_results=True
            )
            seqs1 = mprs1.run()
            sa_seq1 = seqs1[0].split("\t")[1]

            uniprot_id2 = raw_data[3]
            struc_type2 = raw_data[4].value
            chain2 = raw_data[5].value

            protein_list2 = [(uniprot_id2, struc_type2, chain2)]
            mprs2 = MultipleProcessRunnerSimplifier(
                protein_list2, pdb2sequence, n_process=2, return_results=True
            )
            seqs2 = mprs2.run()
            sa_seq2 = seqs2[0].split("\t")[1]
            return sa_seq1, sa_seq2


def uniprot2pdb(uniprot_ids, nprocess=20):
    from utils.downloader import AlphaDBDownloader

    os.makedirs(STRUCTURE_HOME, exist_ok=True)
    af2_downloader = AlphaDBDownloader(
        uniprot_ids, "pdb", save_dir=STRUCTURE_HOME, n_process=20
    )
    af2_downloader.run()


def pdb2sequence(process_id, idx, row_tuple, writer):

    # print("="*100)
    # print(row_tuple)
    # print("="*100)
    uniprot_id = row_tuple[0].split(".")[0]  #
    struc_type = row_tuple[1]  # PDB or AF2
    chain = row_tuple[2]

    if struc_type == "AF2":
        plddt_mask = True
        chain = "A"
    else:
        plddt_mask = False

    try:
        pdb_path = f"{STRUCTURE_HOME}/{uniprot_id}.pdb"
        cif_path = f"{STRUCTURE_HOME}/{uniprot_id}.cif"
        if Path(pdb_path).exists():
            seq = get_struc_seq(
                FOLDSEEK_PATH,
                pdb_path,
                [chain],
                process_id=process_id,
                plddt_mask=plddt_mask,
            )[chain][-1]
        elif Path(cif_path).exists():
            seq = get_struc_seq(
                FOLDSEEK_PATH,
                cif_path,
                [chain],
                process_id=process_id,
                plddt_mask=plddt_mask,
            )[chain][-1]
        else:
            raise BaseException(
                f"The {uniprot_id}.pdb/{uniprot_id}.cif file doesn't exists!"
            )
        writer.write(f"{uniprot_id}\t{seq}\n")

    except Exception as e:
        print(f"Error: {uniprot_id}, {e}")


def get_accumulate_grad_samples(num_samples):
    if num_samples > 3200:
        return 64
    elif 1600 < num_samples <= 3200:
        return 32
    elif 800 < num_samples <= 1600:
        return 16
    elif 400 < num_samples <= 800:
        return 8
    elif 200 < num_samples <= 400:
        return 4
    elif 100 < num_samples <= 200:
        return 2
    else:
        return 1


def make_config(
    batch_size, max_epochs, learning_rate, base_model, task_type, csv_dataset_path
):
    # training config
    GPU_batch_size = 0
    accumulate_grad_batches = 0
    num_workers = 2
    seed = 20000812

    # lora config
    r = 8
    lora_dropout = 0.0
    lora_alpha = 16

    # dataset config
    val_check_interval=0.5
    limit_train_batches=1.0
    limit_val_batches=1.0
    limit_test_batches=1.0

    mask_struc_ratio=None

    with open('funchub/func_impl/saprot/default.yaml', 'r', encoding='utf-8') as fp:
            Default_config = EasyDict(yaml.safe_load(fp))
    config = copy.deepcopy(Default_config)

    config.model.model_py_path = model_type_dict[task_type]

    if task_type in ["classification", "token_classification", "pair_classification"]:
        config.model.kwargs.num_labels = get_num_labels(csv_dataset_path)

    config.model.kwargs.config_path = base_model
    config.dataset.kwargs.tokenizer = base_model

    # Add timesatmp
    cur_time = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    
    config.model.save_path = Path(get_temp_dir()) / task_type / cur_time / os.path.splitext(os.path.basename(csv_dataset_path))[0]

    if task_type in ["regression", "pair_regression"]:
        config.model.kwargs.extra_config = {}
        config.model.kwargs.extra_config.attention_probs_dropout_prob=0
        config.model.kwargs.extra_config.hidden_dropout_prob=0

    config.model.kwargs.lora_kwargs = EasyDict({
        "is_trainable": True,
        "num_lora": 1,
        "r": r,
        "lora_dropout": lora_dropout,
        "lora_alpha": lora_alpha,
        "config_list": []})


    config.Trainer.accelerator = "gpu" if torch.cuda.is_available() else "cpu"

    # epoch
    config.Trainer.max_epochs = int(max_epochs)
    # test only: load the existing model
    if config.Trainer.max_epochs == 0:
        config.model.save_path = config.model.kwargs.lora_kwargs.config_list[
            0
        ].lora_config_path

    # learning rate
    config.model.lr_scheduler_kwargs.init_lr = float(learning_rate)

    # trainer
    config.Trainer.limit_train_batches = limit_train_batches
    config.Trainer.limit_val_batches = limit_val_batches
    config.Trainer.limit_test_batches = limit_test_batches
    config.Trainer.val_check_interval = val_check_interval

    # strategy
    strategy = {
        # - deepspeed
        # 'class': 'DeepSpeedStrategy',
        # 'stage': 2
        # - None
        # 'class': None,
        # - DP
        # 'class': 'DataParallelStrategy',
        # - DDP
        # 'class': 'DDPStrategy',
        # 'find_unused_parameter': True
    }
    config.Trainer.strategy = strategy

    data_type = get_data_type(csv_dataset_path)
    check_task_type_and_data_type(task_type, data_type)

    csv_dataset_path = get_SA_sequence_by_data_type(data_type, csv_dataset_path)
    check_column_label_and_stage(csv_dataset_path)

    dataset_name = os.path.basename(csv_dataset_path).split(".")[0]

    construct_lmdb(csv_dataset_path, LMDB_HOME, dataset_name, task_type)
    lmdb_dataset_path = LMDB_HOME / dataset_name

    config.dataset.dataset_py_path = dataset_type_dict[task_type]

    config.dataset.train_lmdb = str(lmdb_dataset_path / "train")
    config.dataset.valid_lmdb = str(lmdb_dataset_path / "valid")
    config.dataset.test_lmdb = str(lmdb_dataset_path / "test")

    # num_workers
    config.dataset.dataloader_kwargs.num_workers = num_workers

    config.setting.run_mode = "train"

    config.dataset.kwargs.tokenizer = base_model

    # advanced config
    if (GPU_batch_size > 0) and (accumulate_grad_batches > 0):
        config.dataset.dataloader_kwargs.batch_size = GPU_batch_size
        config.Trainer.accumulate_grad_batches = accumulate_grad_batches

    elif (GPU_batch_size == 0) and (accumulate_grad_batches == 0):

        GPU_batch_size_dict = {
            "Tesla T4": 2,
            "NVIDIA L4": 2,
            "NVIDIA A100-SXM4-40GB": 4,
        }
        GPU_name = torch.cuda.get_device_name(0)
        GPU_batch_size = (
            GPU_batch_size_dict[GPU_name] if GPU_name in GPU_batch_size_dict else 2
        )

        if task_type in ["pair_classification", "pair_regression"]:
            GPU_batch_size = int(max(GPU_batch_size / 2, 1))

        config.dataset.dataloader_kwargs.batch_size = GPU_batch_size

        # accumulate_grad_batches
        if batch_size == "Adaptive":

            env = lmdb.open(config.dataset.train_lmdb, readonly=True)

            with env.begin() as txn:
                stat = txn.stat()
                num_samples = stat["entries"]

            accumulate_grad_samples = get_accumulate_grad_samples(num_samples)

        else:
            accumulate_grad_samples = int(batch_size)

    accumulate_grad_batches = max(int(accumulate_grad_samples / GPU_batch_size), 1)

    config.Trainer.accumulate_grad_batches = accumulate_grad_batches

    return config

