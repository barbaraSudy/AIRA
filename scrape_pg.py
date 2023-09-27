import os
import uuid
from hashlib import sha256

from scrapy import Spider
from scrapy.crawler import CrawlerProcess
from actions.scraper import AiraSpider

directory_name = uuid.uuid4().hex
root_dir = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
dir_path = os.path.dirname(f"./outputs/{directory_name}/")
output_path = os.path.join(root_dir, "outputs", directory_name)
os.makedirs(output_path, exist_ok=True)

#TODO: set the output_path in scraper.py and research_agent.py

def makeScrapyClass(urls):
    
    class AiraSpider1(Spider):
        '''Spider class to crawl and write out title and text of the html page for a given url'''
    
        name = "AiraSpider1"
        # the starting url for the spider to crawl
        start_urls = urls  # THESE ARE THE URLS IN reasarch_agent.py

        # settings for the spider such as user agent, download delay, 
        # and number of concurrent requests
        custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0;Win64) \
        AppleWebkit/537.36 (KHTML, like Gecko) \
        Chrome/89.0.4389.82 Safari/537.36',
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 1,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 503, 504, 400, 403, 404, 408],
        'DOWNLOADER_MIDDLEWARES': {
        'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
        'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
        'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
            }
        }
        
        # parse method that is called when the spider is done crawling
        def parse(self, response):
            """_summary_

            Extracts the title, url and text from the html page of a given url
            Writes the files to the given output_path (Must be set in scraper.py)
            
            Yields:
                dictionary of title and text of an html page
            """
            item_elements = {
                "title": response.css("title::text").getall(),
                "url": response.url,
                "text": response.text,
            }
            
            try:
                filename = os.path.join(output_path, f'{sha256(item_elements["url"].encode()).hexdigest()}.txt')

                with open(filename, "w", encoding='utf-8') as file:
                    file.write(f'Scraped text from {item_elements["url"]}:\n\n')
                    file.write(item_elements["text"])
            except:
                filename = os.path.join(output_path, f'{sha256(item_elements["url"].encode()).hexdigest()}.txt')
                
                with open(filename, "w", encoding='utf-8') as file:
                    file.write(f'Could not scrape text from {item_elements["title"]}:\n\n')
            yield {
                "title": response.css("title::text").getall(),
                "url": response.url,
            }
            
    return AiraSpider1

if __name__=="__main__":
    
    ### TO BE ADDED TO research_agent.py
    ### start_urls = self.urls_to_scrape

    start_urls = [
         'https://www.marketwatch.com/investing/stock/ubs',
         'https://www.ubs.com/global/en/investor-relations/financial-information/quarterly-reporting.html', 
         'https://finance.yahoo.com/quote/UBS/',
         'https://www.ubs.com/global/en/investor-relations/financial-information/quarterly-reporting.html',
         'https://www.ubs.com/global/en/media/display-page-ndp/en-20230131-4q22-quarterly-result.html',
         'https://www.cnbc.com/2023/08/31/ubs-posts-29-billion-second-quarter-profit-in-first-results-since-credit-suisse-takeover.html',
         'https://www.ubs.com/global/en/investor-relations.html',
    ]
    
    # Create a CrawlerProcess instance
    process = CrawlerProcess()
    
    #Start crawling process
    process.crawl(makeScrapyClass(start_urls))
    process.start()
    
    # Stop process
    process.stop()