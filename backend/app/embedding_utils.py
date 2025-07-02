import os
import logging
import time
import requests
from typing import List, Optional
from dotenv import load_dotenv

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

def get_embedding(text: str) -> List[float]:
    """
    Get embedding for a text using Ollama API.
    
    Args:
        text: The text to generate embedding for
        
    Returns:
        List[float]: The embedding vector
        
    Raises:
        Exception: If there's an error getting the embedding
    """
    try:
        response = requests.post(
            f"{OLLAMA_API_BASE}/api/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "prompt": text
            },
            timeout=60  # 60 seconds timeout
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        logger.error(f"Error getting embedding: {str(e)}")
        raise

def get_embedding_with_retry(text: str, max_retries: int = MAX_RETRIES) -> Optional[List[float]]:
    """
    Get embedding for text with retry logic.
    
    Args:
        text: The text to generate embedding for
        max_retries: Maximum number of retry attempts
        
    Returns:
        Optional[List[float]]: The embedding vector if successful, None otherwise
    """
    for attempt in range(max_retries):
        try:
            return get_embedding(text)
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                logger.error(f"Failed to get embedding after {max_retries} attempts: {str(e)}")
                return None
            
            retry_delay = EMBEDDING_RETRY_DELAY * (attempt + 1)  # Exponential backoff
            logger.warning(
                f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds... Error: {str(e)}"
            )
            time.sleep(retry_delay)
    
    return None
