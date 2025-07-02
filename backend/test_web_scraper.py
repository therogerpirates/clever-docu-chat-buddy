import logging
import sys
from typing import Optional, Dict
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import asyncio
import tiktoken
from app.web_scraper import WebScraper
from app.llm_utils import get_embedding_with_retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class WebScraperTester:
    """A test class to try different web scraping approaches."""
    
    def __init__(self, headless: bool = True):
        """Initialize the web scraper tester."""
        self.timeout = 30
        self.headless = headless
        self.driver = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
        }
    
    def setup_selenium(self):
        """Set up Selenium WebDriver."""
        try:
            logger.info("Setting up Selenium WebDriver...")
            options = Options()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            self.driver.set_page_load_timeout(self.timeout)
            return True
        except Exception as e:
            logger.error(f"Failed to set up Selenium: {str(e)}")
            return False
    
    def close_selenium(self):
        """Close the Selenium WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def scrape_with_selenium(self, url: str) -> Optional[Dict]:
        """Scrape content using Selenium to handle JavaScript rendering."""
        if not self.driver:
            if not self.setup_selenium():
                return None
        
        try:
            logger.info(f"Scraping with Selenium: {url}")
            self.driver.get(url)
            
            # Wait for JavaScript to load (simple wait, can be improved)
            time.sleep(5)
            
            # Get the page source after JavaScript execution
            page_source = self.driver.page_source
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract title
            title = soup.title.string if soup.title else ''
            
            # Try to find main content
            main_content = self._extract_main_content(soup)
            
            if not main_content:
                logger.warning("No main content found with Selenium")
                return None
                
            return {
                'title': title[:255],
                'text': main_content,
                'source': 'selenium',
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Selenium scraping failed: {str(e)}")
            return None
    
    def scrape_with_requests(self, url: str) -> Optional[Dict]:
        """Scrape content using requests and BeautifulSoup."""
        try:
            logger.info(f"Scraping with requests: {url}")
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = soup.title.string if soup.title else ''
            
            # Try to find main content
            main_content = self._extract_main_content(soup)
            
            if not main_content:
                logger.warning("No main content found with requests")
                return None
                
            return {
                'title': title[:255],
                'text': main_content,
                'source': 'requests',
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Requests scraping failed: {str(e)}")
            return None
    
    def _extract_main_content(self, soup) -> str:
        """Helper method to extract main content from BeautifulSoup object."""
        # Try common content selectors
        selectors = [
            'article',
            'main',
            'div.content',
            'div.article',
            'div.post',
            'div#content',
            'div.main',
            'div.page-content',
            'div.entry-content'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                # Get the largest element (most likely the main content)
                largest_element = max(elements, key=lambda x: len(x.get_text(strip=True)))
                text = largest_element.get_text('\n', strip=True)
                if text and len(text) > 100:  # Only return if substantial content
                    return text
        
        # If no specific content found, try to get all paragraphs
        paragraphs = soup.find_all(['p', 'div'])
        text_chunks = []
        
        for p in paragraphs:
            text = p.get_text('\n', strip=True)
            if text and len(text) > 50:  # Only include substantial paragraphs
                text_chunks.append(text)
        
        return '\n\n'.join(text_chunks) if text_chunks else ''
    
    def test_scraping(self, url: str):
        """Test different scraping methods on the given URL."""
        logger.info(f"\n{'='*80}\nTesting URL: {url}\n{'='*80}")
        
        # Test with requests first (simplest approach)
        logger.info("\n[1/2] Testing with requests...")
        result = self.scrape_with_requests(url)
        self._log_result(result)
        
        # Test with Selenium (for JavaScript-heavy sites)
        logger.info("\n[2/2] Testing with Selenium...")
        result = self.scrape_with_selenium(url)
        self._log_result(result)
        
        self.close_selenium()
    
    def _log_result(self, result: Optional[Dict]):
        """Log the result of a scraping attempt."""
        if not result or not result.get('success', False):
            logger.error("Scraping failed or no content found")
            return
            
        logger.info(f"Successfully scraped with {result.get('source', 'unknown')}")
        logger.info(f"Title: {result.get('title', 'N/A')}")
        logger.info(f"Content length: {len(result.get('text', ''))} characters")
        logger.info("\nFirst 500 characters of content:")
        logger.info("-" * 80)
        logger.info(result.get('text', '')[:500] + "...")
        logger.info("-" * 80)

# --- New test for webscraped data embedding ---
async def test_webscrape_and_embed(url: str, max_tokens: int = 1000):
    print(f"\n[TEST] Scraping and embedding: {url}")
    scraper = WebScraper(timeout=30)
    scraped = scraper.scrape_website(url)
    if not scraped or not scraped.get('text'):
        print("Failed to scrape website or no text found.")
        return
    text = scraped['text']
    print(f"Scraped text length: {len(text)} characters")
    # Chunk using tiktoken (same as WebsiteProcessor)
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = encoding.decode(chunk_tokens)
        if chunk_text.strip():
            chunks.append(chunk_text)
    print(f"Total chunks: {len(chunks)}")
    # Get embedding for each chunk
    for idx, chunk in enumerate(chunks):
        print(f"\nChunk {idx+1}/{len(chunks)} (length: {len(chunk)} chars)")
        try:
            embedding = await get_embedding_with_retry(chunk)
            if embedding:
                print(f"Embedding length: {len(embedding)}")
            else:
                print("Failed to get embedding (empty result)")
        except Exception as e:
            print(f"Error getting embedding: {e}")

if __name__ == "__main__":
    # Example public URL (can be changed)
    url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    asyncio.run(test_webscrape_and_embed(url))
