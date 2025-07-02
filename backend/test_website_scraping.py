import asyncio
import sys
import os
from pathlib import Path
import logging
from typing import Optional, Dict
from datetime import datetime

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.website_processor import WebsiteProcessor
from app.models import File, FileStatus, WebsiteDocument

def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Set up file handler with a timestamp in the filename
    log_file = os.path.join(log_dir, f'test_website_scraping_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, mode='w', encoding='utf-8')
        ]
    )
    
    # Get the root logger and set level
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Add console handler with a higher log level
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger

async def test_website_scraping():
    """Test the website scraping and embedding functionality."""
    logger = setup_logging()
    logger.info("Starting website scraping test...")
    
    db = None
    test_file = None
    test_website = None
    
    try:
        # Initialize database session
        db = SessionLocal()
        
        # Create a test file record
        logger.info("Creating test file record...")
        test_file = File(
            filename="test_website",
            original_filename="test_website",
            file_path="https://example.com",
            file_type="WEBSITE",
            status=FileStatus.PROCESSING,
            is_processed=False,
            chunk_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            user_id=1  # Assuming user ID 1 exists
        )
        db.add(test_file)
        db.commit()
        db.refresh(test_file)
        logger.info(f"Created test file with ID: {test_file.id}")
        
        # Create a test website document
        logger.info("Creating test website document...")
        test_website = WebsiteDocument(
            file_id=test_file.id,
            url="https://example.com",
            title="Test Website",
            description="Test website description",
            domain="example.com",
            status="processing",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(test_website)
        db.commit()
        db.refresh(test_website)
        logger.info(f"Created test website document with ID: {test_website.id}")
        
        # Process the website
        logger.info("Starting website processing...")
        processor = WebsiteProcessor(db)
        logger.info("Created WebsiteProcessor instance")
        
        logger.info("Calling _process_website_background...")
        await processor._process_website_background(
            url="https://example.com",
            website_id=test_website.id,
            file_id=test_file.id
        )
        
        logger.info("Website processing completed successfully!")
        
        # Verify the results
        logger.info("Verifying results...")
        updated_file = db.query(File).filter(File.id == test_file.id).first()
        updated_website = db.query(WebsiteDocument).filter(WebsiteDocument.id == test_website.id).first()
        
        logger.info(f"File status: {updated_file.status}")
        logger.info(f"File is processed: {updated_file.is_processed}")
        logger.info(f"Chunk count: {updated_file.chunk_count}")
        logger.info(f"Website status: {updated_website.status}")
        
        # Print results to console
        print("\n=== Test Results ===")
        print(f"File status: {updated_file.status}")
        print(f"File is processed: {updated_file.is_processed}")
        print(f"Chunk count: {updated_file.chunk_count}")
        print(f"Website status: {updated_website.status}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)
        if db:
            db.rollback()
        raise
        
    finally:
        # Clean up
        if db:
            try:
                if test_website:
                    logger.info("Deleting test website document...")
                    db.delete(test_website)
                if test_file:
                    logger.info("Deleting test file...")
                    db.delete(test_file)
                db.commit()
                logger.info("Test data cleaned up successfully")
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {str(cleanup_error)}")
                if db:
                    db.rollback()
            finally:
                logger.info("Closing database connection")
                db.close()
        


def main():
    """Main function to run the test."""
    print("Starting main function...")  # Debug print
    logger = None
    try:
        print("Setting up logging...")  # Debug print
        # Initialize logging
        logger = setup_logging()
        print("Logging setup complete")  # Debug print
        
        logger.info("Starting website scraping test script")
        
        # Run the test
        logger.info("Running test_website_scraping function")
        print("Running test_website_scraping...")  # Debug print
        asyncio.run(test_website_scraping())
        print("Test completed successfully")  # Debug print
        logger.info("Test completed successfully")
        
    except Exception as e:
        print(f"\nERROR in main: {str(e)}")  # Debug print
        if logger:
            logger.critical(f"Test failed with error: {str(e)}", exc_info=True)
        else:
            print(f"\nCRITICAL ERROR: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        print("\nCheck the latest log file in the 'logs' directory for detailed error information.", file=sys.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    print("Script started")  # Debug print
    sys.exit(main())
