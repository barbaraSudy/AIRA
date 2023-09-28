import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from pathlib import Path
import os
from hashlib import sha256
import scrapy
from scrapy.crawler import CrawlerProcess


from config import Config

FILE_DIR = Path(__file__).parent.parent
CFG = Config()


class Spider(scrapy.Spider):
    def __init__(self, urllist, output_dir):
        self.start_urls = urllist
        self.output_dir = output_dir

    name = "AiraSpider"
    # the starting url for the spider to crawl

    # settings for the spider such as user agent, download delay, 
    # and number of concurrent requests
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0;Win64) \
            AppleWebkit/537.36 (KHTML, like Gecko) \
            Chrome/89.0.4389.82 Safari/537.36',
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 100,
        'RETRY_TIMES': 0,
        'RETRY_HTTP_CODES': [500, 503, 504, 400, 408],
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
        }
    }
    
    # parse method that is called when the spider is done crawling
    def parse(self, response):
        text = ''
        soup = BeautifulSoup(response.text, 'html.parser')
        clean_soup = self.remove_unwanted_tags(soup)
        text = self.extract_main_content(clean_soup)

        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)
        
        if len(text) > 200:
            filename = os.path.join(self.output_dir, f'{sha256(response.url.encode()).hexdigest()}.txt')
            with open(filename, "w", encoding='utf-8') as file:
                file.write(f'Scraped text from {response.url}:\n\n')
                file.write(text)
        # else:
        #     filename = os.path.join(self.output_dir, f'{sha256(response.url.encode()).hexdigest()}.txt')
        #     with open(filename, "w", encoding='utf-8') as file:
        #         file.write(f'Could not scrape text from {response.url}:\n\n')
        # yield {
        #     "text": text
        # }
        yield None

        
    # this code can be refined. 
    def remove_unwanted_tags(self, soup):
        for disclaimer_tag in soup.select('div[class*="Disclaimer__TextContainer"]'):
            disclaimer_tag.decompose()

        for footer_tag in soup.select('div[class*="GlobalFooter__"]'):
            footer_tag.decompose()

        for hidden_tag in soup.select('p[class*="visually-hidden"]'):
            hidden_tag.decompose()

        for data in soup(['style', 'script', 'iframe', 'footer', 'header', 'a', 'nav', 'noscript']):
            data.decompose()

        # dirty_soup = ' '.join(soup.find_all(string=True))
        # remove_allcaps_words = re.sub(r'\b[A-Z]+\b', '', dirty_soup)
        # clean_soup = re.sub("\s\s+", " ", str(remove_allcaps_words))
        return soup

    def extract_content_by_tags(self, soup, extracted_content):
        """Extract content based on a list of tags and classes."""
        # List of possible content selectors
        possible_content_selectors = [
            'article', '.content', '.main-content', '.article-body', 
            '.post-content', '.blog-content', '.story-content', '.news-article',
            '#main-content', '#article-content', '#story-content', '.entry-content',
            '.post-entry', '.article-text', '.article-main', '.article-content',
            '.text-content', '.main-article', '#content-body', '.body-copy',
            '.news-body', '.article-inner', '.full-story', '.story-body'
        ]
        extracted_content = []
        for selector in possible_content_selectors:
            selected_content = soup.select(selector)
            if len(selected_content)>0:
                for content_section in selected_content:
                    text = content_section.get_text(strip=True)
                    extracted_content.append(text) if len(text) > 50 else None
        return extracted_content

    def extract_content_by_density(self, soup, extracted_content, threshold=50):
        """Extract content based on text density above a given threshold."""
        extracted_content = []
        
        for tag in soup.find_all(['div', 'section', 'p', 'h1', 'h2', 'h3', 'h4']):
            # Check if the tag has a parent that's already in our high_density_sections
            parent_tags = tag.find_parents(['div', 'section'])
            if any(parent.get_text(strip=True) in extracted_content for parent in parent_tags):
                continue

            text_length = len(tag.get_text(strip=True))
            child_tags = len(tag.find_all(['p', 'div', 'section', 'article', 'span', 'a', 'li', 'ul', 'ol']))
            
            # Avoid division by zero
            if child_tags == 0:
                continue
            
            density = text_length / child_tags
            tag_text = tag.get_text(strip=True)
            if density > threshold:
                # # Check if any existing content in the list contains the new text or vice versa
                # if not any(existing_text in tag_text or tag_text in existing_text for existing_text in extracted_content):
                extracted_content.append(tag_text)
        
        return extracted_content

    def extract_main_content(self, soup):
        # First remove unwanted tags
        soup = self.remove_unwanted_tags(soup)
        # Use both ways to extract content
        extracted_content = []
        extracted_content.extend(self.extract_content_by_tags(soup, extracted_content))
        extracted_content.extend(self.extract_content_by_density(soup, extracted_content))
        # In case some content is duplicated in extracted_content, remove duplicates 
        # Takes care if strings don't match but contain other entries
        unique_extraced_content = []
        for item in extracted_content:
            if not any(item.lower() in x.lower() for x in unique_extraced_content):
                unique_extraced_content.append(item)
        return "\n\n".join(extracted_content)


class Scraper:
    def scrape_parallel(self, urllist, output_dir):
        c = CrawlerProcess()
        c.crawl(Spider, urllist=urllist, output_dir=output_dir)
        c.start()
        return c