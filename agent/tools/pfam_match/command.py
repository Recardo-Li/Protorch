import requests
import re
import argparse

'''
A retriever for Pfam entry matching. Given a uniprot id, this tool searches for all Pfam entries on the protein and returns the accessions and position ranges of these Pfam entries on the protein. 
You can retrieve the list of Pfam entries matching a protein as a JSON document using URL like this: 'https://www.ebi.ac.uk/interpro/api/entry/pfam/protein/uniprot/P00789/'
'''

class PfamMatchRetriever():
    def __init__(self):
        self.base_url = "https://www.ebi.ac.uk/interpro/api/entry/pfam/protein/uniprot/"

    def search(self, uniprot_id):
        search_url = self.base_url + str(uniprot_id)
        response = requests.get(search_url)
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            res = self.get_match_result(data)

        else:
            res = "There is no data associated with the requested URL, List of endpoints: ['protein', 'uniprot', '{accession}']".format(accession=uniprot_id)
        return res


    def get_match_result(self, data):

        results = data.get("results", [])
        extracted_info = []

        for entry in results:
            metadata = entry.get("metadata", {})
            accession = metadata.get("accession", 'N/A')
            name = metadata.get("name", 'N/A')
            entry_type = metadata.get("type", 'N/A')

            for protein in entry.get("proteins", []):
                for location in protein.get("entry_protein_locations", []):
                    for fragment in location.get("fragments", []):
                        start = fragment.get("start", 'N/A')
                        end = fragment.get("end", 'N/A')
                        extracted_info.append({
                            "accession": accession,
                            "name": name,
                            "type": entry_type,
                            "start": start,
                            "end": end
                        })

        return extracted_info

def main():
    # Load ESMFold
    re = PfamMatchRetriever()
    res = re.search(uniprot_id=args.uniprot_id)
    print(res)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--uniprot_id', type=str, required=True, help="The UniProt ID of the protein to be searched. For example, 'P00789'."
    )

    
    return parser.parse_args()

if __name__ == '__main__':
    """
    EXAMPLE:
    python cmd.py   --uniprot_id "P00789" \
       
    """
    args = get_args()
    main()