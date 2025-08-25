"""
Utility functions module for SaProt Workflow tools
Contains sequence processing, dataset operations, similarity calculations, and other functions
"""

import os
import subprocess
import tempfile
import pandas as pd
import numpy as np
from Bio import SeqIO, Align
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Align import PairwiseAligner
from sklearn.model_selection import train_test_split
import requests
import time


def calculate_sequence_similarity(seq1, seq2):
    """
    Calculate similarity between two sequences
    Args:
        seq1: First sequence
        seq2: Second sequence
    Returns:
        float: Similarity score (0-1)
    """
    aligner = PairwiseAligner()
    aligner.match_score = 2
    aligner.mismatch_score = -1
    aligner.open_gap_score = -2
    aligner.extend_gap_score = -0.5
    
    alignment = aligner.align(seq1, seq2)[0]
    max_len = max(len(seq1), len(seq2))
    similarity = alignment.score / (max_len * 2)  # 归一化到0-1
    return min(similarity, 1.0)


def remove_redundant_sequences(sequences, threshold=0.7):
    """
    Remove redundant sequences based on similarity threshold
    Args:
        sequences: List of sequences, each element as (seq_id, sequence)
        threshold: Similarity threshold
    Returns:
        list: List of unique sequences after redundancy removal
    """
    if not sequences:
        return []
    
    unique_sequences = [sequences[0]]  # 保留第一个序列
    
    for seq_id, sequence in sequences[1:]:
        is_redundant = False
        for _, unique_seq in unique_sequences:
            similarity = calculate_sequence_similarity(sequence, unique_seq)
            if similarity >= threshold:
                is_redundant = True
                break
        
        if not is_redundant:
            unique_sequences.append((seq_id, sequence))
    
    return unique_sequences


def split_sequences_by_similarity(sequences, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, 
                                  redundancy_threshold=0.7, random_state=42):
    """
    根据序列相似度智能划分数据集，确保相似序列不会同时出现在训练集和测试集中
    Args:
        sequences: 序列列表
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
        redundancy_threshold: 相似度阈值
        random_state: 随机种子
    Returns:
        tuple: (train_seqs, val_seqs, test_seqs)
    """
    np.random.seed(random_state)
    
    # 首先进行基于相似度的聚类
    clusters = []
    unassigned = list(sequences)
    
    while unassigned:
        # 选择一个序列作为聚类中心
        center_seq = unassigned.pop(0)
        cluster = [center_seq]
        
        # 找到所有与中心相似的序列
        to_remove = []
        for i, (seq_id, seq) in enumerate(unassigned):
            similarity = calculate_sequence_similarity(center_seq[1], seq)
            if similarity >= redundancy_threshold:
                cluster.append((seq_id, seq))
                to_remove.append(i)
        
        # 移除已分配的序列
        for i in reversed(to_remove):
            unassigned.pop(i)
        
        clusters.append(cluster)
    
    # 随机打乱聚类顺序
    np.random.shuffle(clusters)
    
    # 按比例分配聚类到不同数据集
    n_clusters = len(clusters)
    n_train = int(n_clusters * train_ratio)
    n_val = int(n_clusters * val_ratio)
    
    train_clusters = clusters[:n_train]
    val_clusters = clusters[n_train:n_train + n_val]
    test_clusters = clusters[n_train + n_val:]
    
    # 展平聚类为序列列表
    train_seqs = [seq for cluster in train_clusters for seq in cluster]
    val_seqs = [seq for cluster in val_clusters for seq in cluster]
    test_seqs = [seq for cluster in test_clusters for seq in cluster]
    
    return train_seqs, val_seqs, test_seqs


def download_uniprot_sequences(query, max_results=1000, reviewed=True):
    """
    Download sequences from UniProt
    Args:
        query: Search query
        max_results: Maximum number of results
        reviewed: Whether to return only reviewed entries
    Returns:
        list: List of (uniprot_id, sequence, description) tuples
    """
    base_url = "https://rest.uniprot.org/uniprotkb/search"
    
    # 构建查询参数
    query_string = f"({query})"
    if reviewed:
        query_string += " AND reviewed:true"
    
    params = {
        "query": query_string,
        "format": "fasta",
        "size": min(max_results, 500)  # API限制
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        
        sequences = []
        fasta_content = response.text
        
        # 解析FASTA内容
        from io import StringIO
        fasta_io = StringIO(fasta_content)
        
        for record in SeqIO.parse(fasta_io, "fasta"):
            uniprot_id = record.id.split("|")[1] if "|" in record.id else record.id
            sequence = str(record.seq)
            description = record.description
            sequences.append((uniprot_id, sequence, description))
        
        return sequences
        
    except Exception as e:
        print(f"Error downloading UniProt sequences: {e}")
        return []


def download_domain_annotations(uniprot_ids, database="pfam"):
    """
    Download domain annotation information
    Args:
        uniprot_ids: List of UniProt IDs
        database: Annotation database type
    Returns:
        dict: {uniprot_id: [(start, end, domain_type, description)]}
    """
    annotations = {}
    
    # Should implement real API calls here
    # For demonstration purposes, we return mock data
    for uniprot_id in uniprot_ids:
        domains = []
        num_domains = np.random.randint(1, 4)
        
        for i in range(num_domains):
            start = np.random.randint(1, 200)
            end = start + np.random.randint(20, 100)
            domain_types = ["kinase_domain", "binding_site", "active_site", "transmembrane", "signal_peptide"]
            domain_type = np.random.choice(domain_types)
            description = f"{domain_type} domain {i+1}"
            domains.append((start, end, domain_type, description))
        
        annotations[uniprot_id] = domains
    
    return annotations


def create_fasta_file(sequences, output_path):
    """
    Create FASTA file
    Args:
        sequences: List of (seq_id, sequence, description) tuples
        output_path: Output file path
    """
    records = []
    for seq_id, sequence, description in sequences:
        record = SeqRecord(Seq(sequence), id=seq_id, description=description)
        records.append(record)
    
    with open(output_path, "w") as output_handle:
        SeqIO.write(records, output_handle, "fasta")


def create_domain_annotation_file(annotations, output_path):
    """
    创建结构域注释文件
    Args:
        annotations: {seq_id: [(start, end, domain_type, description)]}
        output_path: 输出文件路径
    """
    rows = []
    for seq_id, domains in annotations.items():
        for start, end, domain_type, description in domains:
            rows.append({
                "seq_id": seq_id,
                "start": start,
                "end": end,
                "domain_type": domain_type,
                "description": description
            })
    
    df = pd.DataFrame(rows)
    df.to_csv(output_path, sep='\t', index=False)


def validate_dataset_format(dataset_file, task_type="classification"):
    """
    验证数据集格式
    Args:
        dataset_file: 数据集文件路径
        task_type: 任务类型 ("classification" 或 "token_classification")
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        df = pd.read_csv(dataset_file)
        
        if task_type == "classification":
            required_columns = ["sequence", "label", "stage"]
            if not all(col in df.columns for col in required_columns):
                return False, f"缺少必需的列: {required_columns}"
            
            # 检查序列格式
            if df["sequence"].isnull().any():
                return False, "序列列包含空值"
            
            # 检查标签
            if df["label"].isnull().any():
                return False, "标签列包含空值"
            
        elif task_type == "token_classification":
            required_columns = ["sequence_id", "position", "residue", "label", "stage"]
            if not all(col in df.columns for col in required_columns):
                return False, f"缺少必需的列: {required_columns}"
        
        return True, "数据集格式正确"
        
    except Exception as e:
        return False, f"读取数据集时出错: {e}"


def estimate_training_time(num_sequences, avg_length, num_epochs, base_model="SaProt_35M"):
    """
    估算训练时间
    Args:
        num_sequences: 序列数量
        avg_length: 平均序列长度
        num_epochs: 训练轮数
        base_model: 基础模型
    Returns:
        float: 估算的训练时间（小时）
    """
    # 简化的时间估算公式
    base_time_per_seq = 0.1 if base_model == "SaProt_35M" else 0.3  # 秒/序列
    
    total_time_seconds = num_sequences * avg_length * num_epochs * base_time_per_seq / 1000
    total_time_hours = total_time_seconds / 3600
    
    return max(total_time_hours, 0.1)  # 最少0.1小时


def check_system_requirements():
    """
    检查系统要求
    Returns:
        dict: 系统状态信息
    """
    import psutil
    import torch
    
    status = {
        "gpu_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "memory_gb": psutil.virtual_memory().total / (1024**3),
        "cpu_count": psutil.cpu_count(),
    }
    
    if torch.cuda.is_available():
        status["gpu_memory_gb"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    
    return status


def log_workflow_progress(log_file, step, message, progress=None):
    """
    记录工作流程进度
    Args:
        log_file: 日志文件路径
        step: 步骤名称
        message: 日志消息
        progress: 进度百分比 (0-100)
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    with open(log_file, "a", encoding="utf-8") as f:
        if progress is not None:
            f.write(f"[{timestamp}] {step} ({progress}%): {message}\n")
        else:
            f.write(f"[{timestamp}] {step}: {message}\n")


if __name__ == "__main__":
    # 测试函数
    print("测试序列相似度计算...")
    seq1 = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSPLHSVYVDQWDWERVMGDGERQFSTLKSTVEAIWAGIKATEAAVSEEFGLAPFLPDQIHFVHSQELLSRYPDLDAKGRERAIAKDLGAVFLVGIGGKLSDGHRHDVRAPDYDDWSTPSELGHAGLNGDILVWNPVLEDAFELSSMGIRVDADTLKHQLALTGDEDRLELEWHQALLRGEMPQTIGGGIGQSRLTMLLLQLPHIGQVQAGVWPAAVRESVPSLL"
    seq2 = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSPLHSVYVDQWDWERVMGDGERQFSTLKSTVEAIWAGIKATEAAVSEEFGLAPFLPDQIHFVHSQELLSRYPDLDAKGRERAIAKDLGAVFLVGIGGKLSDGHRHDVRAPDYDDWSTPSELGHAGLNGDILVWNPVLEDAFELSSMGIRVDADTLKHQLALTGDEDRLELEWHQALLRGEMPQTIGGGIGQSRLTMLLLQLPHIGQVQAGVWPAAVRESVPSLL"
    
    similarity = calculate_sequence_similarity(seq1, seq2)
    print(f"序列相似度: {similarity:.3f}")
    
    print("\n检查系统要求...")
    requirements = check_system_requirements()
    for key, value in requirements.items():
        print(f"{key}: {value}") 