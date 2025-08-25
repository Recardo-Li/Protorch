import argparse

def main():
    parser = argparse.ArgumentParser(description='Convert protein sequence to FASTA format')
    parser.add_argument('--protein_sequence', help='Input protein sequence')
    parser.add_argument('--header',
                       default=None,
                       help='Custom header')
    parser.add_argument('--save_path', help='Path to save the output FASTA file')

    args = parser.parse_args()

    if args.header is None:
        # Generate default header with '>' prefix
        header = f">protein_sequence"
    else:
        # Ensure the header starts with '>'
        if not args.header.startswith('>'):
            header = '>' + args.header
        else:
            header = args.header

    # Output the FASTA formatted content
    with open(args.save_path, 'w') as f:
        f.write(f"{header}\n")
        protein_sequence = args.protein_sequence.replace(" ", "").replace("\n", "")
        f.write(f"{protein_sequence}\n")
    print(f"FASTA file saved to {args.save_path}")

if __name__ == '__main__':
    '''
    EXAMPLE:
    python command.py --protein_sequence "ACDEFGHIKLMNPQRSTVWY" --header "My_Protein" --save_path "output.fasta"
    '''
    main()