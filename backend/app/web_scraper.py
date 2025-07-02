import logging
from typing import Dict, Optional, Tuple, Any
from urllib.parse import urlparse
import trafilatura
from newspaper import Article, Config
import requests
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import atexit

logger = logging.getLogger(__name__)

class WebScraper:
    """A utility class for scraping and extracting content from web pages."""
    
    def __init__(self, timeout: int = 30, headless: bool = True):
        """Initialize the web scraper with configuration.
        
        Args:
            timeout: Timeout in seconds for web requests
            headless: Whether to run browser in headless mode (no GUI)
        """
        self.timeout = timeout
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
        
        # Configure newspaper3k
        self.newspaper_config = Config()
        self.newspaper_config.browser_user_agent = self.headers['User-Agent']
        self.newspaper_config.request_timeout = self.timeout
        self.newspaper_config.fetch_images = False
        self.newspaper_config.memoize_articles = False
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
    
    def scrape_with_newspaper(self, url: str) -> Optional[Dict]:
        """Scrape article content using newspaper3k library."""
        try:
            logger.info(f"Scraping with newspaper3k: {url}")
            article = Article(url, config=self.newspaper_config)
            article.download()
            article.parse()
            
            if not article.text.strip():
                return None
                
            return {
                'title': article.title[:255] if article.title else '',
                'text': article.text,
                'summary': article.meta_description or '',
                'publish_date': str(article.publish_date) if article.publish_date else None,
                'authors': ', '.join(article.authors) if article.authors else '',
                'source': 'newspaper3k',
                'top_image': article.top_image or ''
            }
        except Exception as e:
            logger.warning(f"Newspaper3k failed for {url}: {str(e)}")
            return None
    
    def scrape_with_trafilatura(self, url: str) -> Optional[Dict]:
        """Scrape article content using trafilatura library."""
        try:
            logger.info(f"Scraping with trafilatura: {url}")
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None
                
            result = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                include_links=False,
                output_format='json',
                with_metadata=True
            )
            
            if not result or not result.get('text'):
                return None
                
            return {
                'title': result.get('title', '')[:255],
                'text': result.get('text', ''),
                'summary': result.get('description', ''),
                'publish_date': result.get('date'),
                'authors': ', '.join(result.get('author', [])) if isinstance(result.get('author'), list) else result.get('author', ''),
                'source': 'trafilatura',
                'top_image': result.get('image', '')
            }
        except Exception as e:
            logger.warning(f"Trafilatura failed for {url}: {str(e)}")
            return None
    
    def scrape_with_fallback(self, url: str) -> Optional[Dict]:
        """Fallback scraping method using requests and BeautifulSoup."""
        try:
            logger.info(f"Using fallback scraper for: {url}")
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
                element.decompose()
            
            # Try to get title
            title = ''
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            # Get main content
            content_elements = []
            for tag in ['article', 'main', 'div.content', 'div.article', 'div.post']:
                elements = soup.select(tag)
                for el in elements:
                    text = el.get_text(' ', strip=True)
                    if text and len(text) > 100:  # Only include substantial content
                        content_elements.append(text)
            
            # If no specific content found, try generic approach
            if not content_elements:
                for tag in ['p', 'div']:
                    elements = soup.find_all(tag)
                    for el in elements:
                        text = el.get_text(' ', strip=True)
                        if text and len(text) > 100:
                            content_elements.append(text)
            
            text = '\n\n'.join(content_elements)
            
            if not text.strip():
                return None
                
            return {
                'title': title[:255],
                'text': text,
                'summary': '',
                'publish_date': None,
                'authors': '',
                'source': 'fallback',
                'top_image': ''
            }
            
        except Exception as e:
            logger.warning(f"Fallback scraper failed for {url}: {str(e)}")
            return None
    
    def _setup_selenium(self) -> bool:
        """Set up Selenium WebDriver if not already set up."""
        if self.driver is not None:
            return True
            
        try:
            logger.info("Initializing Selenium WebDriver...")
            options = Options()
            
            if self.headless:
                options.add_argument('--headless')
                
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            
            # Disable images and other resources for faster loading
            prefs = {
                'profile.managed_default_content_settings.images': 2,
                'permissions.default.stylesheet': 2,
                'javascript.enabled': True
            }
            options.add_experimental_option('prefs', prefs)
            
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            self.driver.set_page_load_timeout(self.timeout)
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {str(e)}")
            self.driver = None
            return False
    
    def scrape_with_selenium(self, url: str) -> Optional[Dict]:
        """Scrape website using Selenium to handle JavaScript rendering."""
        if not self._setup_selenium():
            return None
            
        try:
            logger.info(f"Scraping with Selenium: {url}")
            self.driver.get(url)
            
            # Wait for page to load (wait for body tag to be present)
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located(('tag name', 'body'))
            )
            
            # Additional wait for dynamic content
            time.sleep(3)
            
            # Get the page source after JavaScript execution
            page_source = self.driver.page_source
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract title
            title = self.driver.title or ''
            
            # Try to find main content
            main_content = self._extract_main_content(soup)
            
            if not main_content.strip():
                logger.warning("No main content found with Selenium")
                return None
                
            return {
                'title': title[:255],
                'text': main_content,
                'summary': '',
                'publish_date': None,
                'authors': '',
                'source': 'selenium',
                'top_image': ''
            }
            
        except TimeoutException:
            logger.warning(f"Selenium timed out while loading {url}")
            return None
        except WebDriverException as e:
            logger.warning(f"Selenium WebDriver error for {url}: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error with Selenium for {url}: {str(e)}")
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
    
    def cleanup(self):
        """Clean up resources, especially Selenium WebDriver."""
        if self.driver is not None:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("Selenium WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing Selenium WebDriver: {str(e)}")
    
    def scrape_website(self, url: str) -> Optional[Dict]:
        """
        Scrape a website using multiple methods and return the best result.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dict containing the scraped content or None if all methods fail
        """
        logger.info(f"Starting to scrape website: {url}")
        
        # Try newspaper3k first (best for news articles)
        result = self.scrape_with_newspaper(url)
        if result and result.get('text', '').strip():
            logger.info("Successfully scraped with newspaper3k")
            return result
        
        # Then try trafilatura (good for general web pages)
        result = self.scrape_with_trafilatura(url)
        if result and result.get('text', '').strip():
            logger.info("Successfully scraped with trafilatura")
            return result
        
        # Try the fallback method
        result = self.scrape_with_fallback(url)
        if result and result.get('text', '').strip():
            logger.info("Successfully scraped with fallback method")
            return result
            
        # Finally, try Selenium for JavaScript-heavy sites
        result = self.scrape_with_selenium(url)
        if result and result.get('text', '').strip():
            logger.info("Successfully scraped with Selenium")
            return result
        
        logger.error(f"All scraping methods failed for {url}")
        return None


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    scraper = WebScraper()
    test_url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    result = scraper.scrape_website(test_url)
    
    if result:
        print(f"Title: {result['title']}")
        print(f"Source: {result['source']}")
        print(f"Text length: {len(result['text'])} characters")
        print("\nFirst 500 characters:")
        print(result['text'][:500] + "...")
