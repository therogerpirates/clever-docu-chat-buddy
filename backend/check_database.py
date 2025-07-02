import sys
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the parent directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import engine, SessionLocal
from app.models import File, PDFDocument, PDFChunk, CSVDocument, CSVChunk, XLSXDocument, XLSXChunk, User, FileStatus, FileType, UserRole

# Load environment variables
load_dotenv()

def check_tables():
    """Check if all required tables exist."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    required_tables = ['files', 'pdf_documents', 'pdf_chunks', 'csv_documents', 
                      'csv_chunks', 'xlsx_documents', 'xlsx_chunks', 'users', 'file_restrictions']
    
    print("\n=== Checking Tables ===")
    for table in required_tables:
        exists = table in tables
        print(f"{table}: {'✅' if exists else '❌'}")
    
    # Print all tables for debugging
    print("\nAll tables in database:")
    for table in tables:
        print(f"- {table}")

def check_data():
    """Check the data in the database."""
    db = SessionLocal()
    
    try:
        # Check files
        print("\n=== Files ===")
        files = db.query(File).all()
        print(f"Found {len(files)} files")
        for file in files:
            print(f"- ID: {file.id}, Name: {file.original_filename}, Type: {file.file_type}, Status: {file.status}")
            print(f"  Uploaded by: {file.uploaded_by.username if file.uploaded_by else 'Unknown'}")
            print(f"  Restricted to users: {[u.username for u in file.restricted_users]}")
        
        # Check PDF documents and chunks
        print("\n=== PDF Documents ===")
        pdf_docs = db.query(PDFDocument).all()
        print(f"Found {len(pdf_docs)} PDF documents")
        for doc in pdf_docs:
            print(f"- ID: {doc.id}, File ID: {doc.file_id}, Title: {doc.title}")
            chunks = db.query(PDFChunk).filter_by(document_id=doc.id).all()
            print(f"  Chunks: {len(chunks)}")
        
        # Check CSV documents and chunks
        print("\n=== CSV Documents ===")
        csv_docs = db.query(CSVDocument).all()
        print(f"Found {len(csv_docs)} CSV documents")
        for doc in csv_docs:
            print(f"- ID: {doc.id}, File ID: {doc.file_id}")
            chunks = db.query(CSVChunk).filter_by(document_id=doc.id).all()
            print(f"  Chunks: {len(chunks)}")
        
        # Check XLSX documents and chunks
        print("\n=== XLSX Documents ===")
        xlsx_docs = db.query(XLSXDocument).all()
        print(f"Found {len(xlsx_docs)} XLSX documents")
        for doc in xlsx_docs:
            print(f"- ID: {doc.id}, File ID: {doc.file_id}")
            chunks = db.query(XLSXChunk).filter_by(document_id=doc.id).all()
            print(f"  Chunks: {len(chunks)}")
        
        # Check users
        print("\n=== Users ===")
        users = db.query(User).all()
        for user in users:
            print(f"- ID: {user.id}, Username: {user.username}, Role: {user.role}")
            
    except Exception as e:
        print(f"Error checking data: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    check_tables()
    check_data()
