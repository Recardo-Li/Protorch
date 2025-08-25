#!/usr/bin/env python3
"""
Filter FASTA sequences based on matched IDs from MMSeqs2 search results.
"""

import sys
import argparse

def read_fasta_sequences(fasta_path):
    """Read FASTA file and return dictionary of id -> sequence"""
    sequences = {}
    current_id = None
    current_seq = []
    
    with open(fasta_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):
                if current_id is not None:
                    sequences[current_id] = ''.join(current_seq)
                # Extract sequence ID (everything after '>' and before first space)
                current_id = line[1:].split()[0]
                current_seq = []
            else:
                current_seq.append(line)
        
        if current_id is not None:
            sequences[current_id] = ''.join(current_seq)
    
    return sequences

def read_matched_ids(matched_ids_path):
    """Read matched sequence IDs"""
    matched_ids = set()
    try:
        with open(matched_ids_path, 'r') as f:
            for line in f:
                matched_ids.add(line.strip())
    except FileNotFoundError:
        pass
    return matched_ids

def filter_sequences(target_fasta_path, matched_ids_path, output_fasta_path):
    """Filter sequences by removing matched IDs"""
    # Read target sequences
    target_sequences = read_fasta_sequences(target_fasta_path)
    
    # Read matched IDs
    matched_ids = read_matched_ids(matched_ids_path)
    
    # Write filtered sequences (excluding matched ones)
    with open(output_fasta_path, 'w') as out_f:
        for seq_id, sequence in target_sequences.items():
            if seq_id not in matched_ids:
                out_f.write(f'>{seq_id}\n')
                # Write sequence with 80 characters per line
                for i in range(0, len(sequence), 80):
                    out_f.write(sequence[i:i+80] + '\n')
    
    original_count = len(target_sequences)
    removed_count = len(matched_ids)
    filtered_count = original_count - removed_count
    
    print(f"Filtering completed. Original: {original_count}, Filtered: {filtered_count}, Removed: {removed_count}")
    return original_count, filtered_count, removed_count

def main():
    parser = argparse.ArgumentParser(description='Filter FASTA sequences based on matched IDs')
    parser.add_argument('target_fasta', help='Target FASTA file path')
    parser.add_argument('matched_ids', help='File containing matched sequence IDs')
    parser.add_argument('output_fasta', help='Output filtered FASTA file path')
    
    args = parser.parse_args()
    
    filter_sequences(args.target_fasta, args.matched_ids, args.output_fasta)

if __name__ == '__main__':
    main()