import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import json
from pathlib import Path



load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables")

try:
    engine = create_engine(DATABASE_URL)
    # Test the connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("Successfully connected to the database")
except Exception as e:
    print(f"Error connecting to the database: {e}")
    raise

def check_pdf_chunks():
    """Check PDF chunks and their embeddings in the database."""
    with Session(engine) as session:
        # Get count of PDF chunks
        count = session.execute(text("SELECT COUNT(*) FROM pdf_chunks")).scalar()
        print(f"Total PDF chunks in database: {count}")
        
        if count == 0:
            print("No PDF chunks found in the database.")
            return
        
        # Get sample of PDF chunks with their embeddings
        print("\nSample of PDF chunks:")
        print("-" * 80)
        
        # Get first 5 chunks with their document info
        query = """
        SELECT 
            f.original_filename,
            pc.page_number,
            LENGTH(pc.content) as content_length,
            pc.embedding IS NOT NULL as has_embedding,
            json_typeof(pc.embedding) as embedding_type,
            LENGTH(pc.embedding::text) as embedding_length
        FROM pdf_chunks pc
        JOIN pdf_documents p ON pc.document_id = p.id
        JOIN files f ON p.file_id = f.id
        ORDER BY pc.id
        LIMIT 5
        """
        
        results = session.execute(text(query)).fetchall()
        
        if not results:
            print("No PDF chunks found with document information.")
            return
            
        # Print the results in a formatted way
        print(f"{'Filename':<40} | {'Page':<5} | {'Content Len':<10} | {'Has Emb':<7} | {'Emb Type':<10} | {'Emb Len'}")
        print("-" * 100)
        
        for row in results:
            print(f"{row[0][:37]:<40} | {row[1]:<5} | {row[2]:<10} | {str(row[3]):<7} | {str(row[4] or 'N/A'):<10} | {row[5] or 'N/A'}")
        
        # Check if any chunks are missing embeddings
        missing_embeddings = session.execute(
            text("SELECT COUNT(*) FROM pdf_chunks WHERE embedding IS NULL")
        ).scalar()
        
        print(f"\nChunks missing embeddings: {missing_embeddings}")
        
        # Check embedding dimensions (sample first chunk)
        if count > 0:
            embedding_sample = session.execute(
                text("SELECT embedding FROM pdf_chunks WHERE embedding IS NOT NULL LIMIT 1")
            ).scalar()
            
            if embedding_sample:
                try:
                    if isinstance(embedding_sample, str):
                        embedding = json.loads(embedding_sample)
                    else:
                        embedding = embedding_sample
                        
                    if isinstance(embedding, list):
                        print(f"\nSample embedding dimensions: {len(embedding)}")
                        print(f"First 5 values: {embedding[:5]}")
                    else:
                        print(f"\nUnexpected embedding format: {type(embedding)}")
                except Exception as e:
                    print(f"\nError parsing embedding: {e}")

if __name__ == "__main__":
    print("Checking PDF chunks and embeddings...\n")
    check_pdf_chunks()
