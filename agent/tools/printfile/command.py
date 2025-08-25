import os
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', type=str, help='Input file path')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file_path):
        raise FileNotFoundError(f"File not found: {args.file_path}")
    
    # If file size is less than 200KB, print the file content
    file_size = os.path.getsize(args.file_path)
    if file_size < 200 * 1024:
        with open(args.file_path, 'r') as fp:
            print(fp.read())
    else:
        raise ValueError(f"File size exceeds 200KB: {file_size / 1024:.2f} KB")

if __name__ == "__main__":
    """
    EXAMPLE:
    python command.py example/human_FP.fasta
    """
    main()