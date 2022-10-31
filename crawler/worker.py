from threading import Thread

from inspect import getsource
from utils.download import download
from utils import get_logger
import scraper
import time
import data

def printReport():
    print('')
    print('~~~~~~~~~~~~~~~~~~~REPORT~~~~~~~~~~~~~~~~~~~')
    print(f'Number of Unique Found Pages: {len(data.uniqueLinks)}')
    print(f'Number of Unique Crawled Pages: {len(data.crawledUniqueLinks)}')
    print('')
    print(f'Longest Page Found: {data.longestPageFound[0]} with {data.longestPageFound[1]} tokens.')

    sortedTokenCount = sorted(data.tokenCount.items(), key=lambda x: x[1], reverse=True)
    print('')
    print('Most common 50 tokens:')
    numOfTokens = 0
    for k, v in sortedTokenCount:
        if numOfTokens > 50:
            break
        print('    {} -> {}'.format(k,v))
        numOfTokens+=1
    
    print('')
    print('Subdomains in ics.uci.edu:')
    for k, v in data.subDomains.items():
        print(f'    {k}, {len(v)}')


class Worker(Thread):
    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in {"from requests import", "import requests"}} == {-1}, "Do not use requests from scraper.py"
        super().__init__(daemon=True)
        
    def run(self):

        while True:
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                printReport()
                break
            resp = download(tbd_url, self.config, self.logger)
            self.logger.info(
                f"Downloaded {tbd_url}, status <{resp.status}>, "
                f"using cache {self.config.cache_server}.")
            scraped_urls = scraper.scraper(tbd_url, resp)
            for scraped_url in scraped_urls:
                self.frontier.add_url(scraped_url)
            self.frontier.mark_url_complete(tbd_url)
            time.sleep(self.config.time_delay)

