import pandas as pd
import json
import logging
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from .models import CSVDocument
from .database import create_dynamic_table, insert_rows_to_dynamic_table, engine
from .llm_utils import get_groq_chat
from .utils import get_embedding

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# --- Only SQL RAG logic below ---

def process_csv_for_sql_rag(df: pd.DataFrame, file_id: int, original_filename: str):
    """
    Ingest CSV data into a dynamic SQL table for SQL RAG.
    Args:
        df: The pandas DataFrame of the CSV
        file_id: The file's unique ID
        original_filename: The original filename to store in the table
    """
    table_name = f"csv_data_{file_id}"
    columns = [col.lower() for col in df.columns]
    # Create the table
    create_dynamic_table(engine, table_name, columns, original_filename=original_filename)
    # Prepare rows as dicts with lowercased keys to match table columns
    rows = [
        {k.lower(): v for k, v in row.items()}
        for row in df.to_dict(orient='records')
    ]
    # Insert rows (bulk insert)
    insert_rows_to_dynamic_table(engine, table_name, columns, rows, original_filename=original_filename)
    return table_name

async def generate_csv_database_insights(df: pd.DataFrame, original_filename: str) -> str:
    """
    Generate a concise summary for SQL RAG using only column names.
    Args:
        df: The pandas DataFrame of the CSV
        original_filename: The original filename
    Returns:
        str: LLM-generated summary about the table's columns and possible SQL queries
    """
    try:
        columns = list(df.columns)
        analysis_prompt = f"""
You are a data analyst and SQL expert. You are analyzing a database table created from the file: {original_filename}

Table Columns:
{json.dumps(columns, indent=2)}

Please provide a concise summary of what types of SQL queries could be written for this table, based only on the column names. Do not speculate about the data values. List possible query types (e.g., filtering, grouping, aggregations) and mention any columns that look like IDs, dates, or categories. Keep the summary short and focused.

Use double quotes (\"column name\") for column and table names with spaces or special characters, as required by PostgreSQL. Do NOT use backticks.
"""
        chat = await get_groq_chat(temperature=0.2)
        from langchain_core.messages import HumanMessage
        response = await chat.ainvoke([HumanMessage(content=analysis_prompt)])
        summary = response.content.strip()
        return summary
    except Exception as e:
        logger.error(f"Error generating CSV database summary: {str(e)}")
        return f"Table columns: {', '.join(columns)}."

async def process_csv_for_sql_rag_with_insights(df: pd.DataFrame, file_id: int, original_filename: str, db: Session):
    """
    Ingest CSV data into a dynamic SQL table and generate summary for SQL RAG.
    Args:
        df: The pandas DataFrame of the CSV
        file_id: The file's unique ID
        original_filename: The original filename
        db: Database session for storing summary
    Returns:
        tuple: (table_name, summary_embedding)
    """
    table_name = process_csv_for_sql_rag(df, file_id, original_filename)
    summary = await generate_csv_database_insights(df, original_filename)
    summary_embedding = get_embedding(summary)
    csv_doc = db.query(CSVDocument).filter(CSVDocument.file_id == file_id).first()
    if csv_doc:
        csv_doc.header = {
            'summary': summary,
            'summary_embedding': summary_embedding,
            'table_name': table_name
        }
        db.commit()
    return table_name, summary_embedding
