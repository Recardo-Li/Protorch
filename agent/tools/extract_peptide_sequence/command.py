import argparse
import sys
import json

def extract(seq: str, start: int, end: int)->str:
    return seq[start-1:end]

def get_args():
    parser = argparse.ArgumentParser(description="Extract peptide sequence from a protein sequence")
    parser.add_argument("--protein_sequence", type=str, required=True, help="Full protein sequence")
    parser.add_argument("--start", type=int, required=True, help="Start residue index (1-based)")
    parser.add_argument("--end", type=int, required=True, help="End residue index (1-based)")
    return parser.parse_args()

def main():
    args = get_args()

    # Log inputs
    print(f"Processing sequence length:{len(args.protein_sequence)};"
          f"Extracting residues {args.start}-{args.end}", file=sys.stderr)
    
    # Validate
    if args.start < 1 or args.end > len(args.protein_sequence) or args.start >= args.end:
        error_msg = "Invalid start or end index."
        print(json.dumps({"error": error_msg}))
        sys.exit(1)

    # Extact peptide sequence
    peptide = extract(args.protein_sequence, args.start, args.end)

    # Output json result
    result = {"peptiede_sequence": peptide}
    print(json.dumps(result))

if __name__ == "__main__":
    main()
