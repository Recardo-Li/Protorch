import requests
import xml.etree.ElementTree as ET
import datetime
import argparse

class PubmedRetriever():
    def __init__(self, max_papers, start_date, end_date):
        self.max_papers = max_papers
        self.start_date = start_date
        self.end_date = end_date
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Accept-Encoding': 'identity'
        }
        return
    
    def search(self, query):
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            'db': 'pubmed',
            'term': query,
            'mindate': self.start_date,
            'maxdate': self.end_date,
            'retmax': self.max_papers,
            'sort': 'relevance',
        }
        response = requests.get(url, params=params, headers=self.headers)
        root = ET.fromstring(response.text)
        id_list = root.find('IdList')
        ids = [id.text for id in id_list.findall('Id')] if id_list is not None else []
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

    def get_articles_info(self, xml_data):
        root = ET.fromstring(xml_data)
        articles = []
        for article in root.findall(".//PubmedArticle"):
            # Extract DOI
            doi = None
            for elocation_id in article.findall(".//ELocationID"):
                if elocation_id.attrib.get('EIdType') == 'doi':
                    doi = elocation_id.text
                    break
            doi = doi if doi else 'DOI not found'
            
            # Extract Title
            article_title = article.find(".//ArticleTitle")
            title = article_title.text if article_title is not None else 'Title not found'
            
            # Extract Date
            formatted_date = "Date not found"
            pubmed_dates = article.findall(".//PubMedPubDate[@PubStatus='pubmed']")
            for date_id in pubmed_dates:
                year_elem = date_id.find('Year')
                month_elem = date_id.find('Month')
                day_elem = date_id.find('Day')
                if year_elem is not None and year_elem.text is not None:
                    year = year_elem.text
                    month = month_elem.text if (month_elem is not None and month_elem.text) else '01'
                    day = day_elem.text if (day_elem is not None and day_elem.text) else '01'
                    formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    break
            
            # Extract Abstract
            abstract = "Abstract not found"
            abstract_elem = article.find(".//Abstract")
            if abstract_elem is not None:
                abstract_texts = []
                for text_elem in abstract_elem.findall(".//AbstractText"):
                    if text_elem.text:
                        abstract_texts.append(text_elem.text)
                if abstract_texts:
                    abstract = " ".join(abstract_texts)
            
            articles.append({
                "title": title,
                "date": formatted_date,
                "doi": doi,
                "abstract": abstract
            })
        return articles

    def query(self, query):
        id_results = self.search(query)
        if not id_results:
            return []
        all_paper_xml_results = self.fetch_details(id_results)
        results = self.get_articles_info(all_paper_xml_results)
        return results

def main():
    re = PubmedRetriever(max_papers=args.max_papers, 
                         start_date=args.start_date if args.start_date != "" else (datetime.datetime.today() - datetime.timedelta(days=3*365)).strftime('%Y-%m-%d'), 
                         end_date=args.end_date if args.end_date != "" else datetime.datetime.today().strftime('%Y-%m-%d'))
    res = re.query(query=args.keywords)
    print(res)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--keywords', type=str, required=True, help='A term to search within all articles on pubmed server'
    )
    parser.add_argument(
        '--max_papers', type=str, default='25', help='The maximum number of articles you want to get. Default is 25'
    )
    parser.add_argument(
        '--start_date', type=str, default='', help='The date from which you want to start searching for articles'
    )
    parser.add_argument(
        '--end_date', type=str, default='', help='The date up to which you want to search for articles'
    )
    
    return parser.parse_args()

if __name__ == '__main__':
    """
    EXAMPLE:
    python command.py   --keywords "protein" \
                    --max_papers "10" \
                    --start_date "2024-03-19" \
                    --end_date "2025-01-01"
    """
    args = get_args()
    main()