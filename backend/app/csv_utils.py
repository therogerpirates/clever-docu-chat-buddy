import pandas as pd
import json
import logging
import time
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from .models import CSVDocument, CSVChunk
from .utils import get_embedding

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

def save_csv_chunks_to_db(db: Session, file_id: int, chunks: List[Dict], batch_size: int = 10) -> 'CSVDocument':
    """Save chunks to the database in batches."""
    try:
        # Create CSV document record
        csv_doc = CSVDocument(
            file_id=file_id,
            row_count=len(chunks),
            column_count=len(json.loads(chunks[0]['content'])) if chunks else 0
        )
        db.add(csv_doc)
        db.commit()
        db.refresh(csv_doc)
        
        # Save chunks in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            db_chunks = [
                CSVChunk(
                    document_id=csv_doc.id,
                    row_number=chunk['row_number'],
                    content=chunk['content'],
                    embedding=chunk['embedding']
                )
                for chunk in batch
            ]
            db.bulk_save_objects(db_chunks)
            db.commit()
            logger.info(f"Saved {len(db_chunks)} chunks to database (batch {i//batch_size + 1})")
            
        return csv_doc
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving chunks to database: {str(e)}")
        raise

def process_csv_with_embeddings(df: pd.DataFrame, db: Session, file_id: int, batch_size: int = 10) -> Dict[str, Any]:
    """Process a CSV file and generate embeddings for each row."""
    try:
        # Convert all string columns to lowercase
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.lower()
        
        # Get metadata
        total_rows = len(df)
        metadata = {
            'row_count': total_rows,
            'column_count': len(df.columns)
        }
        
        # Process rows in batches
        all_chunks = []
        for idx, row in df.iterrows():
            try:
                # Convert row to string representation
                row_content = row.to_dict()
                content_str = json.dumps(row_content, ensure_ascii=False)
                
                # Get embedding for the row with retry logic
                embedding = get_embedding_with_retry(content_str)
                
                all_chunks.append({
                    'row_number': idx + 1,  # 1-based indexing
                    'content': content_str,
                    'embedding': embedding
                })
                
                # Log progress
                if (idx + 1) % 10 == 0 or (idx + 1) == total_rows:
                    logger.info(f"Processed {idx + 1}/{total_rows} rows ({(idx + 1)/total_rows:.1%})")
                    
            except Exception as e:
                logger.error(f"Error processing row {idx + 1}: {str(e)}")
                continue
        
        # Save chunks to database
        if all_chunks:
            csv_doc = save_csv_chunks_to_db(db, file_id, all_chunks, batch_size)
            metadata['csv_document_id'] = csv_doc.id
        
        return {
            'status': 'success',
            'metadata': metadata,
            'chunks_processed': len(all_chunks)
        }
        
    except Exception as e:
        logger.error(f"Error processing CSV with embeddings: {str(e)}")
        raise
