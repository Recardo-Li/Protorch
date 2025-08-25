import requests
import re
import json
import requests
import argparse
'''
a simple retriever for Pfam database. Since original Pfam website has been deprecated and all data is hosted on Interpro. We send request to interpro to get result.
The input should be PF accession(unique ID). Results should contain: 
1. Family name
2. Description
3. Wikipedia
4. Literature
'''

class PfamEntryRetriever():

    def __init__(self):
        self.base_url = "https://www.ebi.ac.uk/interpro/api/entry/pfam/"

        return

    def get_entry_accession(self, data):

        accession = data.get('metadata', {}).get('accession', 'N/A')
        return accession

    def get_name(self, data):
        name_info = data.get('metadata', {}).get('name', {})
        name = name_info.get('name', 'N/A')
        return name

    def get_type(self, data):
        type = data.get('metadata', {}).get('type', 'N/A')
        return type

    def get_description(self, data):

        descriptions = data.get('metadata', {}).get('description', [])
        if descriptions:
            description = descriptions[0].get('text', 'N/A')
            description = re.sub('<[^<]+?>', '', description)
        else:
            description = 'N/A'
        return description

    def get_wikipedia(self, data):

        wikipedia_info = data.get('metadata', {}).get('wikipedia', [])
        if wikipedia_info:
            wikipedia = wikipedia_info[0].get('extract', 'N/A')
            wikipedia = re.sub('<[^<]+?>', '', wikipedia)
        else:
            wikipedia = 'N/A'
        return wikipedia

    def fetch_combine_results(self, data):
        """
        综合name, description, wikipedia信息，返回一个dict
        """
        result = {
            'name': self.get_name(data),
            'type': self.get_type(data),
            'description': self.get_description(data),
            'wikipedia': self.get_wikipedia(data)
        }
        return result


    def search(self, family_id):
        search_url = self.base_url + str(family_id)
        response = requests.get(search_url)
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            res = self.fetch_combine_results(data)

        else:
            res = "There is no data associated with the requested URL, List of endpoints: ['entry', 'pfam', '{accession}']".format(accession = family_id)
        return res

def main():
    # Load ESMFold
    re = PfamEntryRetriever()
    res = re.search(family_id=args.family_id)
    print(res)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--family_id', type=str, required=True, help="The accession ID of the Pfam entry to be searched. This ID typically starts with 'PF' followed by five digits, for example, 'PF00001'"
    )

    
    return parser.parse_args()

if __name__ == '__main__':
    """
    EXAMPLE:
    python cmd.py   --family_id "PF00069" \
       
    """
    args = get_args()
    main()