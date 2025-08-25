import argparse
import os
import requests
import sys
from datetime import datetime

def download_pdb_file(pdb_id: str, save_dir: str) -> bool:
    """
    Download a PDB file based on the given PDB ID and save it to the specified directory.

    Parameters:
        - pdb_id (str): PDB ID to download (e.g., '1A2B')
        - save_dir (str): Directory path where the PDB file will be saved

    Returns:
        - bool: True if the download is successful, False otherwise
    """
    url = f"https://files.rcsb.org/download/{pdb_id}.cif"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            save_path = f"{save_dir}/{pdb_id}.cif"

            with open(save_path, 'wb') as file:
                file.write(response.content)

            print(f"Successfully downloaded PDB file: {pdb_id}")
            print(f"File saved at: {save_path}")
            return True
        else:
            print(f"Failed to download PDB file. The server responded with status code: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while downloading the PDB file: {str(e)}")
        return False


def main():
    """
    Main function to handle command line arguments and trigger PDB file download.

    Usage Example:
    python download_pdb.py --pdb_id 1A2B --save_dir ./downloads
    """
    parser = argparse.ArgumentParser(description='Download PDB file based on given PDB ID')
    required_args = parser.add_argument_group('required arguments')
    required_args.add_argument('--pdb_id', type=str, help='PDB ID to download')
    required_args.add_argument('--save_dir', type=str, help='Directory path where the PDB file will be saved')

    start_time = datetime.now()
    print(f"Download starting at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    args = parser.parse_args()

    if not args.pdb_id or not args.save_dir:
        parser.print_help()
        sys.exit(1)

    if os.path.exists(f"{args.save_dir}/{args.pdb_id}.pdb"):
        print(f"PDB file {args.pdb_id}.pdb already exists in {args.save_dir}. Overwriting...")
    
    download_success = download_pdb_file(args.pdb_id, args.save_dir)

    end_time = datetime.now()
    duration_insec = (end_time - start_time).total_seconds()
    print(f"Download completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time taken: {duration_insec}")


if __name__ == "__main__":
    """
    Script entry point.

    Usage Example:
    python command.py --pdb_id 1A2B --save_dir .
    """
    main()