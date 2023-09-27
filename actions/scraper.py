from typing import Any, Optional
import requests
from urllib.parse import urljoin
from multiprocessing.pool import ThreadPool
from bs4 import BeautifulSoup
from selenium import webdriver
import threading
from pathlib import Path
import queue
from multiprocessing import Pool
import os
from hashlib import sha256
import logging

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scrapy import cmdline, Spider
from config import Config
import uuid

import sys

# LOGGER.setLevel(logging.WARNING)
FILE_DIR = Path(__file__).parent.parent
CFG = Config()

directory_name = uuid.uuid4().hex
root_dir = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
dir_path = os.path.dirname(f"./outputs/{directory_name}/")
output_path = os.path.join(root_dir, "outputs", directory_name)
os.makedirs(output_path, exist_ok=True)

class AiraSpider(Spider):
    
    name = "aira"
    # the starting url for the spider to crawl
    start_urls = [] #will get set in research_agent
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
        # get the title of the page
        title = response.css("title::text").get()
        # get all the paragraphs from the page
        text = response.css("p::text").get()
        print(f"Text of {title}: {text}")
        try:
            filename = os.path.join(output_path, f'{sha256(url.encode()).hexdigest()}.txt')
            with open(filename, "w", encoding='utf-8') as file:
                file.write(f'Scraped text from {title}:\n\n')
                file.write(text)
        except:
            filename = os.path.join(output_path, f'{sha256(url.encode()).hexdigest()}.txt')
            with open(filename, "w", encoding='utf-8') as file:
                file.write(f'Could not scrape text from {title}:\n\n')
        return text


    def crawl(self):
        setting = get_project_settings()
        process = CrawlerProcess(setting)
        process.start()
        return
    

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
