import sys
from unicodedata import category
sys.path.append('.')

import pandas as pd
import csv
import yaml
import torch
import lmdb
from tqdm import tqdm

from sklearn.model_selection import train_test_split
from easydict import EasyDict
from utils.seed import setup_seed
from utils.module_loader import *
from fairscale.nn.model_parallel.initialize import initialize_model_parallel
from typing import Tuple

if __name__ == "__main__":
    # config_file="config/selector_uniprot.yaml"
    # with open(config_file, 'r', encoding='utf-8') as r:
    #     config = EasyDict(yaml.safe_load(r))

    # if config.setting.seed:
    #     setup_seed(config.setting.seed)

    # # set os environment variables
    # for k, v in config.setting.os_environ.items():
    #     if v is not None and k not in os.environ:
    #         os.environ[k] = str(v)

    #     elif k in os.environ:
    #         # override the os environment variables
    #         config.setting.os_environ[k] = os.environ[k]

    # # Only the root node will print the log
    # if config.setting.os_environ.NODE_RANK != 0:
    #     config.Trainer.logger = False


    # with open('dataset/protqa/protqa_train.tsv', 'w', newline='') as tsvfile:
    #     writer = csv.writer(tsvfile, delimiter='\t')
        
    #     # 写入头部
    #     writer.writerow(['seqs', 'foldseeks', 'templates', 'questions', 'answers', 'raw_text_lists', 'protein_embeds', 'protein_atts', 'category'])

    #     data_module = load_dataset(config.dataset)
    #     for batch in data_module.train_dataloader():
    #         data, category = batch
    #         # 写入数据
    #         writer.writerow([
    #             data['seqs'][0],
    #             data['foldseeks'][0],
    #             data['templates'][0],
    #             data['questions'][0],
    #             data['answers'][0],
    #             ','.join(data['raw_text_lists'][0]),  # 将列表转换为逗号分隔的字符串
    #             data['protein_embeds'],
    #             data['protein_atts'],
    #             category[0]
    #         ])

    # with open('dataset/protqa/protqa_val.tsv', 'w', newline='') as tsvfile:
    #     writer = csv.writer(tsvfile, delimiter='\t')
        
    #     # 写入头部
    #     writer.writerow(['seqs', 'foldseeks', 'templates', 'questions', 'answers', 'raw_text_lists', 'protein_embeds', 'protein_atts', 'category'])

    #     data_module = load_dataset(config.dataset)
    #     for batch in data_module.val_dataloader():
    #         data, category = batch
    #         # 写入数据
    #         writer.writerow([
    #             data['seqs'][0],
    #             data['foldseeks'][0],
    #             data['templates'][0],
    #             data['questions'][0],
    #             data['answers'][0],
    #             ','.join(data['raw_text_lists'][0]),  # 将列表转换为逗号分隔的字符串
    #             data['protein_embeds'],
    #             data['protein_atts'],
    #             category[0]
    #         ])

    # with open('dataset/protqa/protqa_test.tsv', 'w', newline='') as tsvfile:
    #     writer = csv.writer(tsvfile, delimiter='\t')
        
    #     # 写入头部
    #     writer.writerow(['seqs', 'foldseeks', 'templates', 'questions', 'answers', 'raw_text_lists', 'protein_embeds', 'protein_atts', 'category'])

    #     data_module = load_dataset(config.dataset)
    #     for batch in data_module.test_dataloader():
    #         data, category = batch
    #         # 写入数据
    #         writer.writerow([
    #             data['seqs'][0],
    #             data['foldseeks'][0],
    #             data['templates'][0],
    #             data['questions'][0],
    #             data['answers'][0],
    #             ','.join(data['raw_text_lists'][0]),  # 将列表转换为逗号分隔的字符串
    #             data['protein_embeds'],
    #             data['protein_atts'],
    #             category[0]
    #         ])
            
    # df = pd.read_csv('dataset/protqa/protqa_train.tsv', sep='\t')
    # core_data = ['questions', 'category']
    # df_core = df[core_data]
    # df_unique = df_core.drop_duplicates()
    # df_unique.to_csv('dataset/uniprotqa/uniprotqa_train.tsv', sep='\t', index=False)

    # df = pd.read_csv('dataset/protqa/protqa_val.tsv', sep='\t')
    # core_data = ['questions', 'category']
    # df_core = df[core_data]
    # df_unique = df_core.drop_duplicates()
    # df_unique.to_csv('dataset/uniprotqa/uniprotqa_val.tsv', sep='\t', index=False)

    # df = pd.read_csv('dataset/protqa/protqa_test.tsv', sep='\t')
    # core_data = ['questions', 'category']
    # df_core = df[core_data]
    # df_unique = df_core.drop_duplicates()
    # df_unique.to_csv('dataset/uniprotqa/uniprotqa_test.tsv', sep='\t', index=False)

#     df_train = pd.read_csv('dataset/uniprotqa/uniprotqa_train.tsv', sep='\t')
#     df_val = pd.read_csv('dataset/uniprotqa/uniprotqa_val.tsv', sep='\t')
#     df_test = pd.read_csv('dataset/uniprotqa/uniprotqa_test.tsv', sep='\t')

#     df = pd.concat([df_train, df_val, df_test], ignore_index=True)

#     df.drop_duplicates()

#     last_column = df.columns[-1]

# # 使用 stratify 参数按照最后一列进行均分
#     train_val_df, test_df = train_test_split(df, test_size=0.2, stratify=df[last_column], random_state=42)
#     train_df, val_df = train_val_df = train_test_split(train_val_df, test_size=0.125, stratify=train_val_df[last_column], random_state=42)  # 0.125 * 0.8 = 0.1

#     # 保存分割后的数据集
#     train_df.to_csv('dataset/uniprotqa/uniprotqa_train_split.tsv', sep='\t', index=False)
#     val_df.to_csv('dataset/uniprotqa/uniprotqa_val_split.tsv', sep='\t', index=False)
#     test_df.to_csv('dataset/uniprotqa/uniprotqa_test_split.tsv', sep='\t', index=False)

    
    # df = pd.read_csv('dataset/uniprotqa/uniprotqa_train_split.tsv', sep='\t')
    # env = lmdb.open('dataset/uniprotqa/lmdb/train', map_size=1099511627776)

    # with env.begin(write=True) as txn:
    #     for idx, row in tqdm(df.iterrows(), total=len(df)):
    #         key = str(idx).encode('ascii')
    #         value = "\t".join(row.values.astype(str)).encode('utf-8')
    #         txn.put(key, value)

    # env.close()

    env = lmdb.open('dataset/uniprotqa/lmdb/train', map_size=1099511627776)
    txn = env.begin()
    cursor = txn.cursor()
    count = 0
    for key, _ in cursor:
        count += 1
    txn.abort()  # Don't forget to abort the transaction
    env.close()

    env = lmdb.open('dataset/uniprotqa/lmdb/train', map_size=1099511627776)
    with env.begin(write=True) as txn:
        if txn.get(b"length") is None:
            txn.put(b"length", str(count).encode())
    env.close()
    print("finish training build")

    # df = pd.read_csv('dataset/uniprotqa/uniprotqa_val.tsv', sep='\t')
    # env = lmdb.open('dataset/uniprotqa/lmdb/val', map_size=1099511627776)

    # with env.begin(write=True) as txn:
    #     for idx, row in tqdm(df.iterrows(), total=len(df)):
    #         key = str(idx).encode('ascii')
    #         value = "\t".join(row.values.astype(str)).encode('utf-8')
    #         txn.put(key, value)

    # env.close()


    env = lmdb.open('dataset/uniprotqa/lmdb/val', map_size=1099511627776)
    txn = env.begin()
    cursor = txn.cursor()
    count = 0
    for key, _ in cursor:
        count += 1
    txn.abort()  # Don't forget to abort the transaction
    env.close()

    env = lmdb.open('dataset/uniprotqa/lmdb/val', map_size=1099511627776)
    with env.begin(write=True) as txn:
        if txn.get(b"length") is None:
            txn.put(b"length", str(count).encode())
    env.close()
    print("finish val build")

    # df = pd.read_csv('dataset/uniprotqa/uniprotqa_test.tsv', sep='\t')
    # env = lmdb.open('dataset/uniprotqa/lmdb/test', map_size=1099511627776)

    # with env.begin(write=True) as txn:
    #     for idx, row in tqdm(df.iterrows(), total=len(df)):
    #         key = str(idx).encode('ascii')
    #         value = "\t".join(row.values.astype(str)).encode('utf-8')
    #         txn.put(key, value)

    # env.close()


    env = lmdb.open('dataset/uniprotqa/lmdb/test', map_size=1099511627776)
    txn = env.begin()
    cursor = txn.cursor()
    count = 0
    for key, _ in cursor:
        count += 1
    txn.abort()  # Don't forget to abort the transaction
    env.close()

    env = lmdb.open('dataset/uniprotqa/lmdb/test', map_size=1099511627776)
    with env.begin(write=True) as txn:
        if txn.get(b"length") is None:
            txn.put(b"length", str(count).encode())
    env.close()
    print("finish test build")