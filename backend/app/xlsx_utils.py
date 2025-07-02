import pandas as pd
import json
import logging
import time
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from .models import XLSXDocument, XLSXChunk
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

def save_xlsx_chunks_to_db(db: Session, file_id: int, chunks: List[Dict], batch_size: int = 10) -> XLSXDocument:
    """
    Save XLSX chunks to the database in batches.
    
    Args:
        db: Database session
        file_id: ID of the file record
        chunks: List of chunk dictionaries with sheet_name, row_number, content, and embedding
        batch_size: Number of chunks to save in each batch
        
    Returns:
        XLSXDocument: The created XLSX document record
    """
    try:
        # Create XLSX document record
        xlsx_doc = XLSXDocument(
            file_id=file_id,
            sheet_count=len({chunk['sheet_name'] for chunk in chunks}) if chunks else 0,
            row_count=len(chunks),
            column_count=len(json.loads(chunks[0]['content'])) if chunks else 0
        )
        db.add(xlsx_doc)
        db.commit()
        db.refresh(xlsx_doc)
        
        # Save chunks in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            db_chunks = [
                XLSXChunk(
                    document_id=xlsx_doc.id,
                    sheet_name=chunk['sheet_name'],
                    row_number=chunk['row_number'],
                    content=chunk['content'],
                    embedding=chunk['embedding']
                )
                for chunk in batch
            ]
            db.bulk_save_objects(db_chunks)
            db.commit()
            logger.info(f"Saved {len(db_chunks)} XLSX chunks to database (batch {i//batch_size + 1})")
            
        return xlsx_doc
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving XLSX chunks to database: {str(e)}")
        raise

def process_xlsx_with_embeddings(file_path: str, db: Session, file_id: int, batch_size: int = 10) -> Dict[str, Any]:
    """
    Process an XLSX file and generate embeddings for each row in each sheet.
    
    Args:
        file_path: Path to the XLSX file
        db: Database session
        file_id: ID of the file record
        batch_size: Number of chunks to process in each batch
        
    Returns:
        dict: Processing results with metadata and status
    """
    try:
        # Read all sheets
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        
        # Get metadata
        metadata = {
            'sheet_count': len(sheet_names),
            'row_count': 0,
            'column_count': 0
        }
        
        # Process each sheet
        all_chunks = []
        for sheet_idx, sheet_name in enumerate(sheet_names, 1):
            try:
                logger.info(f"Processing sheet {sheet_idx}/{len(sheet_names)}: {sheet_name}")
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Skip empty sheets
                if df.empty:
                    logger.warning(f"Skipping empty sheet: {sheet_name}")
                    continue
                
                # Update metadata
                metadata['row_count'] += len(df)
                metadata['column_count'] = max(metadata['column_count'], len(df.columns))
                
                # Convert all string columns to lowercase
                for col in df.columns:
                    if df[col].dtype == 'object':
                        df[col] = df[col].astype(str).str.lower()
                
                # Process each row
                for idx, row in df.iterrows():
                    try:
                        # Convert row to string representation
                        row_content = row.to_dict()
                        content_str = json.dumps(row_content, ensure_ascii=False)
                        
                        # Get embedding for the row with retry logic
                        embedding = get_embedding_with_retry(content_str)
                        
                        all_chunks.append({
                            'sheet_name': sheet_name,
                            'row_number': idx + 1,  # 1-based indexing
                            'content': content_str,
                            'embedding': embedding
                        })
                        
                        # Log progress every 10 rows or on last row
                        if (len(all_chunks) % 10 == 0) or (sheet_idx == len(sheet_names) and idx == len(df) - 1):
                            logger.info(f"Processed {len(all_chunks)} total rows (current sheet: {sheet_name}, row {idx + 1}/{len(df)})")
                            
                    except Exception as row_error:
                        logger.error(f"Error processing row {idx + 1} in sheet {sheet_name}: {str(row_error)}")
                        continue
                        
            except Exception as sheet_error:
                logger.error(f"Error processing sheet {sheet_name}: {str(sheet_error)}")
                continue
        
        # Save all chunks to database
        if all_chunks:
            xlsx_doc = save_xlsx_chunks_to_db(db, file_id, all_chunks, batch_size)
            metadata['xlsx_document_id'] = xlsx_doc.id
        
        return {
            'status': 'success',
            'metadata': metadata,
            'chunks_processed': len(all_chunks)
        }
        
    except Exception as e:
        logger.error(f"Error processing XLSX with embeddings: {str(e)}")
        raise
