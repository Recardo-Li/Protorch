import json
from urllib import request
from bs4 import BeautifulSoup
from tqdm import tqdm
from datetime import datetime, timedelta, date
import requests
"""
A simple tool to retrieve biorxiv articles for a given search query using crawlers. for each article, return its title, date, doi and biorxiv link.
"""


class BiorxivRetriever():
    def __init__(self, search_engine='biorxiv', max_papers=25, start_date=datetime.today() - timedelta(days=3*365), end_date=datetime.today()):
        assert search_engine in ['biorxiv', 'rxivist']
        self.search_engine = search_engine
        self.search_url = 'https://www.biorxiv.org/search/'
        self.max_papers = max_papers
        self.start_date = start_date
        self.end_date = end_date
        self.headers  = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        self.proxies = {
            'http': 'http://10.16.4.37:4780',
            'https': 'http://10.16.4.37:4780',
        }
        return


    def _get_all_links(self, page_soup_articles, base_url="https://www.biorxiv.org"):

        links = []
        for link in page_soup_articles:
            link_tag = link.find('a', href=True)['href']
            if link_tag is not None:
                link = base_url + link_tag
            else:
                link = None

            links.append(link)

        return links

    def _get_all_titles(self, page_soup_articles):
        titles = []
        # titles += [article.find('span', attrs={'class': 'highwire-cite-title'}).text.strip() if article.find('span',attrs={'class': 'highwire-cite-title'}) is not None else None for article in page_soup_articles]
        for article in page_soup_articles:
            title_tag = article.find('span', attrs={'class': 'highwire-cite-title'})
            if title_tag is not None:
                title = title_tag.text.strip()
            else:
                title = None
            titles.append(title)

        return titles

    def _get_all_dois(self, page_soup_articles):
        dois = []

        for article in page_soup_articles:
            doi_tag = article.find('span', attrs={'class': 'highwire-cite-metadata-doi'})
            if doi_tag is not None:
                doi = doi_tag.text.strip()
                doi = doi.replace('doi:', '').strip()
            else:
                doi = None
            dois.append(doi)

        return dois

    def _get_all_dates(self, page_soup_articles):
        dates = []

        for article in page_soup_articles:
            div_element = article.find('div', attrs={'data-pisa': True})
            if div_element is not None:
                data_pisa_master = div_element.get('data-pisa')
                if data_pisa_master:
                    date_parts = data_pisa_master.strip().split(';')[1].split('.')[0:3]
                    formatted_date = '-'.join(date_parts)
                    dates.append(formatted_date)

        return dates

    def _format_search_url(self, query):
        search_url = self.search_url
        search_url += query

        # format start and end date
        start_date = str(self.start_date)
        end_date = str(self.end_date)
        date_str = 'limit_from%3A' + start_date + '%20limit_to%3A' + end_date
        search_url += '%20' + date_str

        ## fixed formatting
        num_page_results = 75
        search_url += '%20numresults%3A' + str(num_page_results) + '%20format_result%3Acondensed' + '%20sort%3Arelevance-rank'

        return search_url




    def _get_title_date_doi_link_biorxiv(self, query):
        '''

        :param query: user query, only keywords
        :return: a list of papers. Each element is a dict that contains title, date, doi and link of the papers retrieved.
        '''
        url = self._format_search_url(query)
        # use user-agent to solve anti-crawler problem: http.client.RemoteDisconnected: Remote end closed connection without response


        response_content = requests.get(url=url, headers=self.headers, proxies=self.proxies)
        # page_html = request.urlopen(url_object).read().decode("utf-8")

        page_soup = BeautifulSoup(response_content.text, "lxml")
        articles = page_soup.find_all(attrs={'class': 'search-result'}) # articles of page soup

        titles = self._get_all_titles(articles)
        dates = self._get_all_dates(articles)
        dois = self._get_all_dois(articles)
        links = self._get_all_links(articles)

        max_papers = min(len(titles), int(self.max_papers))
        papers = [
            {
                "title": title,
                "date": date,
                "doi": doi,
                "link": link
            }
            for title, date, doi, link in
            zip(titles[:max_papers], dates[:max_papers], dois[:max_papers], links[:max_papers])
        ]

        return papers


    def query(self, query):

        # search_url
        query = query.replace(' ', '%20')

        if self.search_engine == 'biorxiv':
            papers = self._get_title_date_doi_link_biorxiv(query)
        else:
            raise Exception('None implemeted search engine: {}'.format(
                self.search_engine))

        return papers

if __name__ == '__main__':
    # print(datetime.today())
    re = BiorxivRetriever(max_papers=50, start_date="2024-06-01", end_date=date.today())
    res = re.query(query="protein")
    print(res)
    print(len(res))