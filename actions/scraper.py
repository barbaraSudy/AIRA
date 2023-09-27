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


from selenium import webdriver
from selenium.common.exceptions import TimeoutException

from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.remote.remote_connection import LOGGER
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import chromedriver_autoinstaller
from config import Config

# LOGGER.setLevel(logging.WARNING)
FILE_DIR = Path(__file__).parent.parent
CFG = Config()

#chromedriver_autoinstaller.install() #Installs the latest compat version of chromedriver

class Scraper:
    def __init__(self):
        self.threadLocal = threading.local()
        self.drivers = set()
        self.chromeOptions = webdriver.ChromeOptions()
        self.chromeOptions.add_argument(f"user-agent={CFG.user_agent}")
        self.chromeOptions.add_argument('--headless')
        self.chromeOptions.add_argument("--enable-javascript")
        self.chromeOptions.add_argument("--no-sandbox")
        self.chromeOptions.add_experimental_option('excludeSwitches', ['enable-logging'])

    def get_driver(self):
        driver = getattr(self.threadLocal, 'driver', None)
        if driver is None:
            driver = webdriver.Chrome(options=self.chromeOptions)
            driver.set_page_load_timeout(10)
            setattr(self.threadLocal, 'driver', driver)
            self.drivers.add(driver)
        return driver

    def close_all_drivers(self):
        for driver in self.drivers:
            driver.quit()

    def scrape_url(self, url, output_dir):
        """Scrape text from a website using selenium

        Args:
            url (str): The url of the website to scrape

        Returns:
            text (str): The text scraped from the website
        """
        text = ''
        try:
            driver = self.get_driver()
            driver.get(url)
            WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            clean_soup = self.remove_unwanted_tags(soup)
            text = self.extract_main_content(clean_soup)

            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)
        except TimeoutException:
            print(f"Timeout error for URL: {url}")
            driver.quit()
        except Exception as e:
            print(f"Error for URL {url}: {e}")
            driver.quit()
        finally:
            try:
                filename = os.path.join(output_dir, f'{sha256(url.encode()).hexdigest()}.txt')
                with open(filename, "w", encoding='utf-8') as file:
                    file.write(f'Scraped text from {url}:\n\n')
                    file.write(text)
            except:
                filename = os.path.join(output_dir, f'{sha256(url.encode()).hexdigest()}.txt')
                with open(filename, "w", encoding='utf-8') as file:
                    file.write(f'Could not scrape text from {url}:\n\n')
        return text

    def scrape_parallel(self, urllist, output_dir):
        # Prepare arguments for starmap
        args = [(url, output_dir) for url in urllist]
        scraped_texts = ThreadPool(CFG.concurrent_browsers).starmap(self.scrape_url, args)
        self.close_all_drivers()
        return scraped_texts
        
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
