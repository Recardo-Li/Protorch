import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

"""
A simple tool to retrieve biorxiv articles for a given search query. Need to install Biopython package. For each article, return its title, date and doi.
"""

class PubmedRetriever():

    def __init__(self, max_papers=25, start_date=datetime.today() - timedelta(days=3*365), end_date=datetime.today()):
        self.max_papers = max_papers
        self.start_date = start_date
        self.end_date = end_date
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Accept-Encoding': 'identity'
        }

        self.proxies = {
            'http': 'http://10.16.4.37:4780',
            'https': 'http://10.16.4.37:4780',
        }
        return

    def search(self, query):
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            'db': 'pubmed',
            'term': query,
            'mindate': self.start_date,
            'maxdate': self.end_date,
            'retmax':self.max_papers,
            'sort': 'relevance',
        }
        response = requests.get(url, params=params, headers=self.headers)
        root = ET.fromstring(response.text)

        id_list = root.find('IdList')
        ids = [id.text for id in id_list.findall('Id')]
        return ids

    def fetch_details(self, id_list):
        ids = ','.join(id_list)
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            'id': ids,
            'retmode': 'xml',
            'db': 'pubmed'
        }

        response = requests.get(url, params=params, headers=self.headers)
        return response.text
    


    def get_titles_dois_dates(self, xml_data):

        root = ET.fromstring(xml_data)
        dois = []
        titles = []
        dates = []
        for article in root.findall(".//PubmedArticle"):
            doi = None
            title = None

            # DOI
            for elocation_id in article.findall(".//ELocationID"):
                if elocation_id.attrib.get('EIdType') == 'doi':
                    doi = elocation_id.text
            dois.append(doi if doi else 'DOI not found')

            # Title
            article_title = article.find(".//ArticleTitle")
            if article_title is not None:
                title = article_title.text
            titles.append(title if title else 'Title not found')

            # Date added to pubmed
            for date_id in article.findall(".//PubMedPubDate"):
                if date_id.attrib.get('PubStatus') == 'pubmed':

                    year = date_id.find('Year').text
                    month = date_id.find('Month').text.zfill(2)  
                    day = date_id.find('Day').text.zfill(2)  
                    formatted_date = f"{year}-{month}-{day}"

            dates.append(formatted_date)


        # format return results
        papers = [
            {
                "title": title,
                "date": date,
                "doi": doi,
            }
            for title, date, doi in
            zip(titles, dates, dois)
        ]

        return papers

    def query(self, query):
        # id_results = self.search(query)
        # all_papers = []
        # # 分批次处理ID
        # for i in range(0, len(id_results), 2):
        #     id_chunk = id_results[i:i+2]
        #     xml_data = self.fetch_details(id_chunk)
        #     papers = self.get_titles_dois_dates(xml_data)
        #     all_papers.extend(papers)


        # return all_papers
        id_results = self.search(query)
        all_paper_xml_results = self.fetch_details(id_results)
        results = self.get_titles_dois_dates(all_paper_xml_results)

        return results

if __name__ == '__main__':

    retriever = PubmedRetriever(max_papers=20, start_date='2020-01-01', end_date='2024-07-01')
    results = retriever.query(query="CRISPR-Cas9 gene editing")
    print(results)


