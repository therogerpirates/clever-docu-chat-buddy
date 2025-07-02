import logging
import re
import urllib.parse
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import tiktoken
import asyncio

from sqlalchemy.orm import Session

from .models import File, FileStatus, WebsiteDocument, WebsiteChunk
from .llm_utils import get_embedding_with_retry
from .web_scraper import WebScraper

logger = logging.getLogger(__name__)

class WebsiteProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    async def process_website(self, url: str, file_id: int, current_user_id: int) -> Dict:
        """Process a website URL, scrape its content, and store it in the database."""
        try:
            # Create a new file record for the website
            website_file = File(
                filename=f"website_{int(datetime.utcnow().timestamp())}",
                original_filename=url,
                file_path=url,
                file_type="WEBSITE",
                status=FileStatus.PROCESSING,
                uploaded_by_id=current_user_id,
                file_metadata={"url": url}
            )
            self.db.add(website_file)
            self.db.commit()
            self.db.refresh(website_file)
            
            # Create website document
            website_doc = WebsiteDocument(
                file_id=website_file.id,
                url=url,
                status="processing",
                document_metadata={"url": url}
            )
            self.db.add(website_doc)
            self.db.commit()
            
            # Start processing in the background
            await self._process_website_background(url, website_doc.id, website_file.id)
            
            return {
                "status": "processing",
                "file_id": website_file.id,
                "website_id": website_doc.id,
                "url": url
            }
            
        except Exception as e:
            logger.error(f"Error processing website {url}: {str(e)}", exc_info=True)
            raise
    
    async def _process_website_background(self, url: str, website_id: int, file_id: int):
        """Background task to process website content using the WebScraper."""
        logger.info(f"Starting background processing for website: {url}")
        
        try:
            # Initialize the web scraper
            scraper = WebScraper(timeout=30)
            
            # Scrape the website
            scraped_data = await asyncio.get_event_loop().run_in_executor(
                None,  # Uses default executor (ThreadPoolExecutor)
                lambda: scraper.scrape_website(url)
            )
            
            if not scraped_data or not scraped_data.get('text', '').strip():
                raise ValueError("Failed to extract any content from the website")
            
            title = scraped_data.get('title', url)
            description = scraped_data.get('summary', '')
            content = scraped_data.get('text', '')
            
            logger.info(f"Successfully scraped website: {title}")
            logger.info(f"Content length: {len(content)} characters")
            logger.info(f"Scraped using: {scraped_data.get('source', 'unknown')}")
            
            # Prepare metadata
            metadata = {
                'source': scraped_data.get('source', 'unknown'),
                'title': title,
                'description': description,
                'publish_date': scraped_data.get('publish_date'),
                'authors': scraped_data.get('authors', ''),
                'top_image': scraped_data.get('top_image', '')
            }
            
            if not content.strip():
                raise ValueError("No meaningful content could be extracted from the webpage")
            
            # Update website document with scraped data
            website_doc = self.db.query(WebsiteDocument).filter(WebsiteDocument.id == website_id).first()
            if not website_doc:
                raise ValueError(f"Website document with ID {website_id} not found")
            
            domain = urllib.parse.urlparse(url).netloc
            
            website_doc.title = (title[:247] + '...') if title and len(title) > 250 else title
            website_doc.description = (description[:997] + '...') if description and len(description) > 1000 else description
            website_doc.domain = domain
            website_doc.document_metadata = metadata  # Store full metadata
            website_doc.status = "processing"
            website_doc.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Updated website document with scraped data from {domain}")
            
            # Split content into chunks and create embeddings
            chunks = self._split_into_chunks(content)
            logger.info(f"Split content into {len(chunks)} chunks")
            
            if not chunks:
                raise ValueError("No valid chunks were created from the content")
            
            # Create chunk records with embeddings
            chunk_objects = []
            for i, chunk in enumerate(chunks):
                try:
                    logger.debug(f"Processing chunk {i+1}/{len(chunks)}")
                    # Get embedding with retry logic
                    try:
                        # Directly await the async function
                        embedding = await get_embedding_with_retry(chunk)
                        
                        if embedding is None:
                            logger.error(f"Failed to get embedding for chunk {i} of website {url}")
                            continue  # Skip this chunk if embedding fails
                            
                        # Convert NumPy array to list if needed
                        import numpy as np
                        if isinstance(embedding, np.ndarray):
                            embedding = embedding.tolist()
                        elif not isinstance(embedding, list):
                            logger.error(f"Unexpected embedding type: {type(embedding)}")
                            continue
                            
                        website_chunk = WebsiteChunk(
                            document_id=website_id,
                            chunk_index=i,
                            content=chunk,
                            embedding=embedding,  # Should now be a list
                            chunk_metadata={
                                "chunk_index": i,
                                "word_count": len(chunk.split()),
                                "char_count": len(chunk),
                                "embedding_length": len(embedding) if isinstance(embedding, (list, np.ndarray)) else 0
                            }
                        )
                        chunk_objects.append(website_chunk)
                        logger.debug(f"Created chunk {i+1} with {len(chunk)} characters")
                        
                    except Exception as e:
                        logger.error(f"Error getting embedding for chunk {i}: {str(e)}", exc_info=True)
                        continue  # Continue with next chunk if embedding fails
                        
                except Exception as chunk_error:
                    logger.error(f"Error processing chunk {i}: {str(chunk_error)}", exc_info=True)
                    continue  # Continue with next chunk if processing fails
            
            if not chunk_objects:
                raise ValueError("No chunks were successfully processed")
            
            # Add all chunks to the database in a single transaction
            self.db.bulk_save_objects(chunk_objects)
            
            # Update website document status
            website_doc.status = "processed"
            website_doc.updated_at = datetime.utcnow()
            
            # Update file status
            file = self.db.query(File).filter(File.id == file_id).first()
            if file:
                file.status = FileStatus.READY
                file.is_processed = True
                file.chunk_count = len(chunk_objects)
                file.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Successfully processed website {url} with {len(chunk_objects)} chunks")
            
        except requests.exceptions.RequestException as re:
            error_msg = f"Request error while processing {url}: {str(re)}"
            logger.error(error_msg, exc_info=True)
            self._update_error_status(website_id, file_id, error_msg)
            raise
            
        except Exception as e:
            error_msg = f"Error in background processing of {url}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._update_error_status(website_id, file_id, error_msg)
            raise
    
    def _update_error_status(self, website_id: int, file_id: int, error_message: str):
        """Helper method to update error status in database."""
        try:
            website_doc = self.db.query(WebsiteDocument).filter(WebsiteDocument.id == website_id).first()
            if website_doc:
                website_doc.status = "error"
                website_doc.error_message = error_message[:1000]
                website_doc.updated_at = datetime.utcnow()
                
                file = self.db.query(File).filter(File.id == file_id).first()
                if file:
                    file.status = FileStatus.ERROR
                    file.processing_error = error_message[:1000]
                    file.updated_at = datetime.utcnow()
                
                self.db.commit()
                logger.info("Updated database with error status")
        except Exception as db_error:
            logger.error(f"Error updating error status in database: {str(db_error)}", exc_info=True)
    
    def _split_into_chunks(self, text: str, max_tokens: int = 1000) -> List[str]:
        """Split text into chunks of specified token size."""
        tokens = self.encoding.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), max_tokens):
            chunk_tokens = tokens[i:i + max_tokens]
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)
            
        return chunks
