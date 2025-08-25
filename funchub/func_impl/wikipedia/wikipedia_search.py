import wikipedia
import requests
import time

class WikipediaSearcher:
    def __init__(self, lang='en', max_retries=3, item_num=3):
        """
        Initialize the searcher class with a default language as English.
        """
        wikipedia.set_lang(lang)
        self.item_num = item_num
        self.max_retries = max_retries

    def handle_disambiguation_error(self, title, e):
        # Try to recursively handle disambiguation error by selecting the first valid page
        for option in e.options:
            try:
                summary = wikipedia.summary(option, sentences=2, auto_suggest=False)
                page = wikipedia.page(option, auto_suggest=False)
                return {
                    'title': option,
                    'summary': summary,
                    'url': page.url
                }
            except wikipedia.exceptions.DisambiguationError as new_e:
                return self.handle_disambiguation_error(option, new_e)  # Recursively resolve disambiguation
            except wikipedia.exceptions.PageError:
                continue  # Skip invalid pages
        return None

    def search(self, query):
        """
        Search for protein-related content on Wikipedia and return the top 'item_num' entries
        with their titles, summaries, and URLs.

        :param query: The search keyword provided by the user.
        :return: A list of dictionaries with 'title', 'summary', and 'url' keys for each result.
        """

        attempt = 0
        while attempt < self.max_retries:

            try:
                print(f"Searching Wikipedia for '{query}'...\n")
                results = wikipedia.search(query)

                if not results:
                    return [{"title": "No Results", "summary": "No entries found. Please try a different keyword.", "url": None}]

                # Get the top N results (or fewer if there are not enough results)
                top_results = results[:self.item_num]
                search_results = []

                for title in top_results:
                    try:
                        # Get the page summary and URL
                        summary = wikipedia.summary(title, sentences=2, auto_suggest=False)  # Get the first 3 sentences of the summary
                        page = wikipedia.page(title, auto_suggest=False)  # Get the page object to fetch the URL

                        # Store the result in a dictionary
                        result = {
                            'title': title,
                            'summary': summary,
                            'url': page.url
                        }
                        search_results.append(result)

                    except wikipedia.exceptions.DisambiguationError as e:
                        print(f"DisambiguationError encountered for '{title}'")
                        result = self.handle_disambiguation_error(title, e) # handle disambiguation, recursively find the first valid page.
                        if result:
                            search_results.append(result)
                        else:
                            search_results.append({
                                'title': title,
                                'summary': "Unable to resolve disambiguation.",
                                'url': None
                            })

                    except wikipedia.exceptions.PageError:
                        print(f"{title} :Page does not exist")
                        search_results.append({
                            'title': title,
                            'summary': 'Page does not exist.',
                            'url': None
                        })
                    except Exception as e:
                        print(f"{title} (Error: {e})")
                        search_results.append({
                            'title': title,
                            'summary': f'Error occurred: {e}',
                            'url': None
                        })

                break # If the search is successful, exit the retry loop
            except requests.exceptions.ConnectionError as e:    
                print(f"ConnectionError: {e}. Retrying in 5 seconds...")
                attempt += 1
                time.sleep(5)

        if attempt == self.max_retries:
            return [{"title": "Error", "summary": "Max retries reached. Could not complete the search.", "url": None}]      

        return search_results


# Example usage
if __name__ == "__main__":

    searcher = WikipediaSearcher(item_num=5)
    query = "enzyme"
    results = searcher.search(query)
    print("------",results)

