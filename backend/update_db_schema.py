import logging
import traceback
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from app.database import engine
from app.models import Base, FileStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_db_schema():
    """Update the database schema to add missing columns."""
    try:
        inspector = inspect(engine)
        if 'files' not in inspector.get_table_names():
            logger.error("The 'files' table does not exist. Initialize the database first.")
            return
        
        columns = inspector.get_columns('files')
        column_names = [col['name'] for col in columns]
        logger.info(f"Existing columns in 'files' table: {column_names}")
        
        if 'status' not in column_names:
            logger.info("Adding 'status' column to 'files' table...")
            with engine.connect() as conn:
                # Use raw SQL to add the column with a default value
                conn.execute(text("""
                    ALTER TABLE files
                    ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'PROCESSING'
                """))
                conn.commit()
                logger.info("'status' column added successfully to 'files' table.")
        else:
            logger.info("'status' column already exists in 'files' table. No changes needed.")
            
    except OperationalError as e:
        logger.error(f"Database operation error: {str(e)}")
        logger.error("Ensure your database supports the ALTER TABLE operation and you have the necessary permissions.")
        logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error updating database schema: {str(e)}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    update_db_schema()
