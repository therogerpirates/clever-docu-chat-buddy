import pandas as pd
import json
import logging
import time
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from .pdf_utils import get_embedding

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

EMBEDDING_RETRY_DELAY = int(os.getenv("EMBEDDING_RETRY_DELAY", "5"))  # Seconds to wait between retries
MAX_RETRIES = int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))  # Maximum number of retries for failed embeddings

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

def process_csv_with_embeddings(df: pd.DataFrame) -> Dict[str, Any]:
    """Process a CSV file and generate embeddings for each row."""
    try:
        # Convert all string columns to lowercase
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.lower()
        
        # Get metadata
        metadata = {
            'row_count': len(df),
            'column_count': len(df.columns)
        }
        
        # Process each row
        chunks = []
        for idx, row in df.iterrows():
            try:
                # Convert row to string representation
                row_content = row.to_dict()
                content_str = json.dumps(row_content)
                
                # Get embedding for the row with retry logic
                embedding = get_embedding_with_retry(content_str)
                
                chunks.append({
                    'row_number': idx + 1,  # 1-based indexing
                    'content': content_str,
                    'embedding': embedding
                })
            except Exception as e:
                logger.error(f"Error processing row {idx + 1}: {str(e)}")
                continue
        
        return {
            'metadata': metadata,
            'chunks': chunks
        }
    except Exception as e:
        logger.error(f"Error processing CSV with embeddings: {str(e)}")
        raise
