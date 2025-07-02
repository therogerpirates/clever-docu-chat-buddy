import os
import PyPDF2
import requests
import json
import time
from typing import List, Dict, Any, Optional
import logging
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from .models import PDFDocument, PDFChunk, File

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3:latest")

# Constants for embedding retry logic
EMBEDDING_RETRY_DELAY = int(os.getenv("EMBEDDING_RETRY_DELAY", "5"))  # Seconds to wait between retries
MAX_RETRIES = int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))  # Maximum number of retries


def extract_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    """Extract metadata from a PDF file."""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            info = reader.metadata
            
            return {
                'title': info.get('/Title', ''),
                'author': info.get('/Author', ''),
                'page_count': len(reader.pages)
            }
    except Exception as e:
        logger.error(f"Error extracting PDF metadata: {str(e)}")
        return {
            'title': '',
            'author': '',
            'page_count': 0
        }

def extract_pdf_content(pdf_path: str) -> List[Dict[str, Any]]:
    """Extract content from each page of a PDF file."""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            pages = []
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():  # Only include non-empty pages
                    pages.append({
                        'page_number': i + 1,
                        'content': text
                    })
            
            return pages
    except Exception as e:
        logger.error(f"Error extracting PDF content: {str(e)}")
        return []

def get_embedding(text: str) -> List[float]:
    """Get embedding for a text using Ollama API."""
    try:
        response = requests.post(
            f"{OLLAMA_API_BASE}/api/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "prompt": text
            }
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        logger.error(f"Error getting embedding: {str(e)}")
        raise

def get_embedding_with_retry(text: str, max_retries: int = MAX_RETRIES) -> List[float]:
    """
    Get embedding for text with retry logic.
    
    Args:
        text: Text to get embedding for
        max_retries: Maximum number of retry attempts
        
    Returns:
        List[float]: Embedding vector
    """
    for attempt in range(max_retries):
        try:
            return get_embedding(text)
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                logger.error(f"Failed to get embedding after {max_retries} attempts: {str(e)}")
                raise
                
            retry_delay = EMBEDDING_RETRY_DELAY * (attempt + 1)
            logger.warning(f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    # This should never be reached due to the raise in the loop
    raise Exception("Failed to get embedding after multiple retries")

def process_pdf(pdf_path: str, file_id: int, db: Session) -> Dict[str, Any]:
    """
    Process a PDF file, extract its content, generate embeddings, and save to database.
    
    Args:
        pdf_path: Path to the PDF file
        file_id: ID of the file record in the database
        db: Database session
        
    Returns:
        dict: Processing results with metadata and statistics
    """
    try:
        logger.info(f"Starting PDF processing for file ID: {file_id}")
        start_time = time.time()
        
        # Extract metadata
        metadata = extract_pdf_metadata(pdf_path)
        logger.info(f"Extracted metadata: {metadata}")
        
        # Create PDF document record
        pdf_doc = PDFDocument(
            file_id=file_id,
            title=metadata.get('title', ''),
            author=metadata.get('author', ''),
            page_count=metadata.get('page_count', 0)
        )
        db.add(pdf_doc)
        db.commit()
        db.refresh(pdf_doc)
        
        # Extract content
        pages = extract_pdf_content(pdf_path)
        logger.info(f"Extracted {len(pages)} pages of content")
        
        # Process pages in batches for embedding
        total_chunks = 0
        total_tokens = 0
        
        for page in pages:
            try:
                # Get embedding for the page content
                embedding = get_embedding_with_retry(page['content'])
                
                # Create PDF chunk record
                chunk = PDFChunk(
                    document_id=pdf_doc.id,
                    page_number=page['page_number'],
                    content=page['content'],
                    embedding=embedding
                )
                db.add(chunk)
                total_chunks += 1
                total_tokens += len(page['content'].split())  # Rough token count
                
                # Commit in batches to avoid too many small transactions
                if total_chunks % 10 == 0:
                    db.commit()
            
            except Exception as e:
                logger.error(f"Error processing page {page['page_number']}: {str(e)}")
                continue
        
        # Final commit for any remaining chunks
        db.commit()
        
        # The file status is updated in the calling function (process_file in utils.py)
        # No need to update it here as well
        
        processing_time = time.time() - start_time
        logger.info(f"Completed PDF processing in {processing_time:.2f} seconds. Processed {total_chunks} chunks.")
        
        return {
            'status': 'success',
            'file_id': file_id,
            'total_pages': len(pages),
            'total_chunks': total_chunks,
            'total_tokens': total_tokens,
            'processing_time_seconds': processing_time,
            'metadata': metadata
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        raise