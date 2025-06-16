import os
import shutil
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests
from sqlalchemy.orm import Session

from .models import File, PDFDocument, CSVDocument, XLSXDocument, FileType, RagType, ProcessedData, FileStatus
from .database import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads")

def ensure_upload_dir():
    """Ensure the upload directory exists"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def get_file_type(filename: str) -> FileType:
    """Determine the file type from the filename"""
    ext = filename.lower().split('.')[-1]
    if ext == 'csv':
        return FileType.CSV
    elif ext in ['xlsx', 'xls']:
        return FileType.XLSX
    elif ext == 'pdf':
        return FileType.PDF
    return FileType.OTHER

async def save_uploaded_file(file) -> str:
    """Save an uploaded file and return the file path"""
    ensure_upload_dir()
    
    # Generate a unique filename
    file_uuid = str(uuid.uuid4())
    original_filename = file.filename
    file_extension = original_filename.split('.')[-1].lower()
    stored_filename = f"{file_uuid}.{file_extension}"
    file_path = UPLOAD_DIR / stored_filename
    
    # Save the file
    contents = await file.read()
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    return str(file_path)

def delete_file(file_path: str) -> bool:
    """Delete a file and return True if successful"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False
    return False

def save_file_to_db(file_path: str, file_type: str, description: str, rag_type: str, db: Session) -> File:
    """
    Save file metadata to the database and return the file record.
    """
    try:
        # Create file record
        file_uuid = str(uuid.uuid4())
        file_record = File(
            file_uuid=file_uuid,
            filename=Path(file_path).name,
            original_filename=Path(file_path).name,
            file_path=str(file_path),
            file_type=FileType(file_type.lower()),
            rag_type=RagType(rag_type) if rag_type else None,
            description=description
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)
        return file_record
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving file to database: {str(e)}")
        raise

# Constants for embedding retry logic
EMBEDDING_RETRY_DELAY = int(os.getenv("EMBEDDING_RETRY_DELAY", "5"))  # Seconds to wait between retries
MAX_RETRIES = int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))  # Maximum number of retries

def get_embedding(text: str) -> List[float]:
    """
    Get embedding for a text using Ollama API.
    """
    try:
        ollama_base = os.getenv('OLLAMA_API_BASE', 'http://localhost:11434')
        model = os.getenv('EMBEDDING_MODEL', 'llama2')
        
        response = requests.post(
            f"{ollama_base}/api/embeddings",
            json={
                "model": model,
                "prompt": text
            },
            timeout=60  # 60 seconds timeout
        )
        response.raise_for_status()
        return response.json().get('embedding', [])
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

def process_file(file_path: str, file_type: str, description: str, rag_type: str = "semantic") -> Dict[str, Any]:
    """
    Process an uploaded file based on its type.
    
    Args:
        file_path: Path to the uploaded file
        file_type: Type of the file (pdf, csv, xlsx)
        description: Description of the file
        rag_type: Type of RAG to use (default: "semantic")
        
    Returns:
        dict: Processing result with status and metadata
    """
    db = SessionLocal()
    try:
        # Save file metadata to database
        file_record = save_file_to_db(file_path, file_type, description, rag_type, db)
        
        # Update file status to PROCESSING
        file_record.status = FileStatus.PROCESSING
        db.commit()
        
        # Process file based on type with retry logic
        try:
            if file_type.lower() == 'pdf':
                from .pdf_utils import process_pdf
                result = process_pdf(file_path, file_record.id, db)
            elif file_type.lower() == 'csv':
                from .csv_utils import process_csv_with_embeddings
                result = process_csv_with_embeddings(file_path)
            elif file_type.lower() in ['xlsx', 'xls']:
                from .xlsx_utils import process_xlsx_with_embeddings
                result = process_xlsx_with_embeddings(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Update file status to READY after successful processing
            file_record.status = FileStatus.READY
            db.commit()
            
            return {
                'status': 'success',
                'file_id': file_record.id,
                'file_uuid': str(file_record.file_uuid),
                'filename': file_record.filename,
                'message': 'File processed successfully',
                'result': result
            }
            
        except Exception as process_error:
            # Update file status to ERROR if processing fails
            file_record.status = FileStatus.ERROR
            db.commit()
            logger.error(f"Error processing file {file_path}: {str(process_error)}")
            raise
            
    except Exception as e:
        db.rollback()
        logger.error(f"Error in process_file: {str(e)}")
        raise
    finally:
        db.close()
