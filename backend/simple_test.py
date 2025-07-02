import sys
import os

def main():
    print("Simple test script started")
    print(f"Python version: {sys.version.split()[0]}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Try to import required modules
    try:
        import logging
        from datetime import datetime
        from sqlalchemy.orm import Session
        from app.database import SessionLocal
        from app.website_processor import WebsiteProcessor
        print("All required modules imported successfully")
    except ImportError as e:
        print(f"Error importing modules: {e}")
        return 1
    
    print("Simple test completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
