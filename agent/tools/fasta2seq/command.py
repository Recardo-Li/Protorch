# File: command.py
# This script is designed to be called as a subprocess.
# It parses a FASTA file and prints the structured result as a JSON string to stdout.

import argparse
import json
import sys

from Bio import SeqIO


def main():
    """
    Main function to parse command-line arguments and run the FASTA parsing.
    """
    parser = argparse.ArgumentParser(
        description="Parse a FASTA file and output sequence records as JSON."
    )
    parser.add_argument(
        "--fasta_file",
        type=str,
        required=True,
        help="The FASTA file containing the protein sequences to be parsed."
    )
    args = parser.parse_args()

    sequence_records = []
    try:
        # Use SeqIO.parse for robust FASTA parsing
        for record in SeqIO.parse(args.fasta_file, "fasta"):
            # Create a dictionary for each record, which is a standard and robust format.
            record_dict = {
                "id": record.id,
                "description": record.description,
                "sequence": str(record.seq)
            }
            sequence_records.append(record_dict)
        
        # Prepare the final output dictionary in the desired format.
        # This matches the 'return_values' definition in the YAML.
        output_data = {"sequence_records": sequence_records}
        
        # Print the entire result as a single JSON string to standard output.
        # This is robust and easy for the parent process to parse.
        print(json.dumps(output_data, indent=2))

    except FileNotFoundError:
        sys.stderr.write(f"Error: The file '{args.fasta_file}' was not found.\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"An error occurred during FASTA parsing: {e}\n")
        sys.exit(1)

if __name__ == '__main__':
    '''
    python command.py --fasta_file example/human_FP.fasta
    '''
    main()
