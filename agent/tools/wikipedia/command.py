import shlex
import wikipedia
import requests
import time
import argparse
import os

class WikipediaSearcher:
    """
    A class to search Wikipedia for scientific terms, designed to be resilient
    to network errors.
    """
    def __init__(self, lang='en', max_retries=3, max_items=3, delay=5):
        """
        Initialize the searcher class.

        :param lang: Wikipedia language edition (e.g., 'en', 'zh').
        :param max_retries: Maximum number of retries for a failed network request.
        :param max_items: The number of top search results to process.
        :param delay: Seconds to wait between retries.
        """
        wikipedia.set_lang(lang)
        self.max_items = int(max_items)
        self.max_retries = int(max_retries)
        self.delay = int(delay)
        # The actual proxy setup is now handled outside this class, before it's
        # instantiated, making the class more reusable.

    def _execute_with_retry(self, func, *args, **kwargs):
        """
        A private helper method to execute any function with a retry mechanism
        for network-related errors.

        :param func: The function to execute (e.g., wikipedia.search).
        :param args: Positional arguments for the function.
        :param kwargs: Keyword arguments for the function.
        :return: The result of the function or raises the last exception.
        """
        attempt = 0
        while attempt < self.max_retries:
            try:
                # The 'requests' library, used by 'wikipedia', automatically
                # picks up proxies from environment variables. We don't need
                # to do anything special here.
                return func(*args, **kwargs)
            except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
                print(f"Network error in '{func.__name__}': {e}. Retrying in {self.delay} seconds... (Attempt {attempt + 1}/{self.max_retries})")
                attempt += 1
                time.sleep(self.delay)
            except Exception as e:
                print(f"An unexpected error occurred in '{func.__name__}': {e}")
                raise e
        
        raise requests.exceptions.ConnectionError(f"Max retries ({self.max_retries}) reached for function '{func.__name__}'.")

    def _handle_disambiguation_error(self, title, e, depth=0, max_depth=3):
        """
        Recursively handle a disambiguation error by selecting the first valid page.
        Added a depth limit to prevent infinite recursion.

        :param title: The original title that caused the error.
        :param e: The DisambiguationError exception object.
        :param depth: Current recursion depth.
        :param max_depth: Maximum recursion depth.
        :return: A result dictionary or None.
        """
        if depth >= max_depth:
            print(f"Max recursion depth reached for disambiguation of {shlex.quote(title)}.")
            return None

        for option in e.options:
            try:
                summary = self._execute_with_retry(wikipedia.summary, option, sentences=2, auto_suggest=False)
                page = self._execute_with_retry(wikipedia.page, option, auto_suggest=False)
                print(f"Resolved disambiguation for {shlex.quote(title)} -> '{option}'")
                return {
                    'title': option,
                    'summary': summary,
                    'url': page.url
                }
            except wikipedia.exceptions.DisambiguationError as new_e:
                return self._handle_disambiguation_error(option, new_e, depth=depth + 1, max_depth=max_depth)
            except wikipedia.exceptions.PageError:
                continue
            except requests.exceptions.ConnectionError:
                print(f"Could not resolve option '{option}' due to network issues.")
                continue
        return None

    def search(self, query):
        """
        Search for protein-related content on Wikipedia and return the top 'max_items' entries
        with their titles, summaries, and URLs.

        :param query: The search keyword provided by the user.
        :return: A list of dictionaries with 'title', 'summary', and 'url' keys for each result.
        """
        search_results = []
        if len(query) > 300:
            print("Warning: Query is too long. Trucating to 300 characters...")
            query = query[:300]
        
        try:
            print(f"Searching Wikipedia for {shlex.quote(query)}...")
            results = self._execute_with_retry(wikipedia.search, query)

            if not results:
                print("No results found.")
                return []

            top_results = results[:self.max_items]
            print(f"Found {len(top_results)} results to process.\n")

            for title in top_results:
                print(f"--- Processing: {title} ---")
                try:
                    summary = self._execute_with_retry(wikipedia.summary, title, sentences=2, auto_suggest=False)
                    page = self._execute_with_retry(wikipedia.page, title, auto_suggest=False)
                    result = {'title': title, 'summary': summary, 'url': page.url}
                    search_results.append(result)

                except wikipedia.exceptions.DisambiguationError as e:
                    print(f"DisambiguationError for {shlex.quote(title)}. Attempting to resolve...")
                    result = self._handle_disambiguation_error(title, e)
                    if result:
                        search_results.append(result)
                    else:
                        search_results.append({'title': title, 'summary': "Unable to resolve disambiguation.", 'url': None})

                except wikipedia.exceptions.PageError:
                    print(f"PageError: The page {shlex.quote(title)} does not exist.")
                    search_results.append({'title': title, 'summary': 'Page does not exist.', 'url': None})
                except requests.exceptions.ConnectionError as e:
                    print(f"Failed to process {shlex.quote(title)} after multiple retries: {e}")
                    search_results.append({'title': title, 'summary': 'Could not retrieve data due to persistent network errors.', 'url': None})
                except Exception as e:
                    print(f"An unexpected error occurred for {shlex.quote(title)}: {e}")
                    search_results.append({'title': title, 'summary': f'An unexpected error occurred: {e}', 'url': None})
            
            return search_results

        except requests.exceptions.ConnectionError as e:
            print(f"Fatal: Could not complete initial search for {shlex.quote(query)} due to network errors.")
            return [{"title": "Error", "summary": str(e), "url": None}]
        except Exception as e:
            print(f"A fatal unexpected error occurred during search: {e}")
            return [{"title": "Fatal Error", "summary": str(e), "url": None}]

def get_args():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description="Search Wikipedia with network resilience.")
    parser.add_argument(
        '--query', type=str, required=True, help='The keywords to search on Wikipedia (e.g., "hemoglobin").'
    )
    parser.add_argument(
        '--max_items', type=int, default=3, help='The maximum number of results to retrieve. Default is 3.'
    )
    parser.add_argument(
        '--lang', type=str, default='en', help="Wikipedia language edition ('en', 'zh', etc.). Default is 'en'."
    )
    # --- NEW ARGUMENT ---
    parser.add_argument(
        '--proxy', type=str, default=None, 
        help='Proxy server URL (e.g., "http://127.0.0.1:7890" or "socks5://127.0.0.1:1080"). Overrides environment variables.'
    )
    return parser.parse_args()

def main():
    """Main execution function."""
    args = get_args()
    
    # --- NEW PROXY HANDLING LOGIC ---
    # Priority 1: Use the --proxy command-line argument if provided.
    if args.proxy:
        print(f"Using proxy specified via command line: {args.proxy}")
        # Set environment variables for the current process. This is the
        # cleanest way to make the `requests` library (used by `wikipedia`)
        # use the proxy.
        os.environ['HTTP_PROXY'] = args.proxy
        os.environ['HTTPS_PROXY'] = args.proxy
    
    # Priority 2: Check for existing environment variables if --proxy is not used.
    elif os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY'):
        proxy_info = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
        print(f"Using proxy from environment variables: {proxy_info}")
    
    # Priority 3: No proxy.
    else:
        print("No proxy specified or found in environment. Using direct connection.")

    searcher = WikipediaSearcher(lang=args.lang, max_items=args.max_items)
    results = searcher.search(query=args.query)
    
    print("\n--- Final Results ---")
    for i, res in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"  Title: {res.get('title')}")
        print(f"  URL: {res.get('url')}")
        print(f"  Summary: {res.get('summary')}")
    print("---------------------\n")


if __name__ == '__main__':
    """
    EXAMPLE USAGE:
    
    # Basic search (no proxy)
    python command.py --query "CRISPR"
    
    # Using the new --proxy argument (HIGHEST PRIORITY)
    python command.py --query "p53 protein" --proxy "http://127.0.0.1:7890"
    
    # Using environment variables (works if --proxy is not set)
    # On Linux/macOS:
    # export HTTPS_PROXY="http://127.0.0.1:7890"
    # python command.py --query "p53 protein"
    """
    main()
