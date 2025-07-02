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
from .database import create_dynamic_table, insert_rows_to_dynamic_table, engine
from .llm_utils import get_groq_chat, get_embedding

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

async def generate_xlsx_database_insights(file_path: str, original_filename: str) -> str:
    """
    Generate database insights using LLM for XLSX data.
    Args:
        file_path: Path to the XLSX file
        original_filename: The original filename
    Returns:
        str: Generated insights about the database structure and data
    """
    try:
        # Read all sheets
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        
        # Analyze each sheet
        sheets_info = []
        total_rows = 0
        all_columns = set()
        
        for sheet_name in sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            if df.empty:
                continue
                
            total_rows += len(df)
            all_columns.update(df.columns)
            
            # Prepare column information for this sheet
            columns_info = []
            for col in df.columns:
                col_type = str(df[col].dtype)
                unique_count = df[col].nunique()
                null_count = df[col].isnull().sum()
                sample_values = df[col].dropna().head(3).tolist()
                
                columns_info.append({
                    'name': col,
                    'type': col_type,
                    'unique_values': unique_count,
                    'null_count': null_count,
                    'sample_values': sample_values
                })
            
            sheets_info.append({
                'sheet_name': sheet_name,
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': columns_info
            })
        
        # Create the analysis prompt
        analysis_prompt = f"""
You are a data analyst and SQL expert. You are analyzing a multi-sheet database created from the Excel file: {original_filename}

File Structure:
- Total Sheets: {len(sheet_names)}
- Total Rows Across All Sheets: {total_rows}
- Unique Columns Across All Sheets: {len(all_columns)}

Sheet Details:
{json.dumps(sheets_info, indent=2)}

Please provide a comprehensive analysis including:
1. Multi-sheet database schema overview
2. Data types and their implications for SQL queries
3. Key insights about the data structure across sheets
4. Potential use cases for SQL analysis (including JOINs between sheets)
5. Important columns for filtering, grouping, and aggregation
6. Data quality observations across sheets
7. Suggested SQL query patterns for this multi-sheet dataset
8. How to effectively query data that spans multiple sheets

Focus on providing insights that would help users write effective SQL queries against this multi-sheet data, including when to use JOINs and how to structure queries for cross-sheet analysis.
"""

        # Get LLM response
        chat = await get_groq_chat(temperature=0.3)
        from langchain_core.messages import HumanMessage
        
        response = await chat.ainvoke([HumanMessage(content=analysis_prompt)])
        insights = response.content
        
        return insights
        
    except Exception as e:
        logger.error(f"Error generating XLSX database insights: {str(e)}")
        return f"Database analysis for {original_filename}: {len(sheet_names)} sheets, {total_rows} total rows. Sheets: {', '.join(sheet_names)}"

def process_xlsx_for_sql_rag(file_path: str, file_id: int, original_filename: str):
    """
    Ingest XLSX data into a dynamic SQL table for SQL RAG.
    Args:
        file_path: Path to the XLSX file
        file_id: The file's unique ID
        original_filename: The original filename to store in the table
    """
    excel_file = pd.ExcelFile(file_path)
    sheet_names = excel_file.sheet_names
    all_rows = []
    columns_set = set()
    for sheet_name in sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        if df.empty:
            continue
        df.columns = [col.lower() for col in df.columns]
        for row in df.to_dict(orient='records'):
            row['sheet_name'] = sheet_name
            all_rows.append(row)
        columns_set.update(df.columns)
    columns = list(columns_set) + ['sheet_name']
    table_name = f"xlsx_data_{file_id}"
    create_dynamic_table(engine, table_name, columns, original_filename=original_filename)
    insert_rows_to_dynamic_table(engine, table_name, columns, all_rows, original_filename=original_filename)
    return table_name

async def process_xlsx_for_sql_rag_with_insights(file_path: str, file_id: int, original_filename: str, db: Session):
    """
    Ingest XLSX data into a dynamic SQL table and generate insights for SQL RAG.
    Args:
        file_path: Path to the XLSX file
        file_id: The file's unique ID
        original_filename: The original filename
        db: Database session for storing insights
    Returns:
        tuple: (table_name, insights_embedding)
    """
    # Create the dynamic table
    table_name = process_xlsx_for_sql_rag(file_path, file_id, original_filename)
    
    # Generate insights using LLM
    insights = await generate_xlsx_database_insights(file_path, original_filename)
    
    # Get embedding for insights
    insights_embedding = await get_embedding(insights)
    
    # Store insights in the database (you may want to create a new model for this)
    # For now, we'll store it in the existing XLSX document
    xlsx_doc = db.query(XLSXDocument).filter(XLSXDocument.file_id == file_id).first()
    if xlsx_doc:
        xlsx_doc.sheet_names = {
            'insights': insights,
            'insights_embedding': insights_embedding,
            'table_name': table_name
        }
        db.commit()
    
    return table_name, insights_embedding
