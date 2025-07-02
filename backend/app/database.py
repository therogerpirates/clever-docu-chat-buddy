from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

try:
    # Create engine with connection pooling and timeout settings
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,  # Recycle connections after 30 minutes
        echo=False  # Set to True for SQL query logging
    )
    
    # Test the connection
    with engine.connect() as connection:
        logger.info("Successfully connected to the database")
except Exception as e:
    logger.error(f"Failed to connect to the database: {str(e)}")
    raise

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Database session dependency for FastAPI endpoints.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def create_dynamic_table(engine, table_name: str, columns: list, original_filename: str = None):
    """
    Dynamically create a table for SQL RAG with columns matching the CSV/XLSX headers.
    Args:
        engine: SQLAlchemy engine
        table_name: Name of the table to create
        columns: List of column names (headers)
        original_filename: The original filename to store as a column (optional)
    """
    metadata = MetaData()
    table_columns = [Column('id', Integer, primary_key=True, autoincrement=True)]
    if original_filename:
        table_columns.append(Column('original_filename', String, nullable=False))
    for col in columns:
        col_lower = col.lower()
        table_columns.append(Column(col_lower, Text, nullable=True))
    table = Table(table_name, metadata, *table_columns)
    metadata.create_all(engine, tables=[table])
    return table


def insert_rows_to_dynamic_table(engine, table_name: str, columns: list, rows: list, original_filename: str = None):
    """
    Insert rows into the dynamically created table for SQL RAG using a single bulk insert for all rows.
    Args:
        engine: SQLAlchemy engine
        table_name: Name of the table
        columns: List of column names (headers)
        rows: List of row dicts (each dict maps column name to value)
        original_filename: The original filename to store in each row (optional)
    """
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    columns_lower = [col.lower() for col in columns]
    insert_data = []
    for row in rows:
        data = {col.lower(): row.get(col) for col in columns}
        if original_filename:
            data['original_filename'] = original_filename
        insert_data.append(data)
    if not insert_data:
        return
    with engine.begin() as conn:
        conn.execute(table.insert(), insert_data)

def get_table_columns(engine, table_name: str):
    """
    Retrieve the list of column names for a given table, excluding 'id' and 'original_filename'.
    Args:
        engine: SQLAlchemy engine
        table_name: Name of the table
    Returns:
        List of column names (str)
    """
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    return [col.name for col in table.columns if col.name not in ('id', 'original_filename')] 