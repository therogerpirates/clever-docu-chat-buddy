from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def update_enum_values():
    db = SessionLocal()
    try:
        # First, update the existing records to use uppercase status
        db.execute(text("""
            UPDATE files 
            SET status = 'PROCESSING' 
            WHERE LOWER(status) = 'processing' OR status IS NULL
        """))
        
        db.execute(text("""
            UPDATE files 
            SET status = 'READY' 
            WHERE LOWER(status) = 'ready'
        """))
        
        db.execute(text("""
            UPDATE files 
            SET status = 'ERROR' 
            WHERE LOWER(status) = 'error'
        """))
        
        # For SQLite, we need to recreate the table to change the CHECK constraint
        # This is a simplified approach - in production, you'd want to back up the data first
        
        # 1. Create a temporary table with the new schema
        # 1. Create a temporary table with the new schema
        # Get the current table definition
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'files'
        """))
        
        # Create the new table with the correct schema
        db.execute(text("""
            CREATE TABLE files_new (
                id INTEGER NOT NULL, 
                file_uuid UUID, 
                filename VARCHAR NOT NULL, 
                original_filename VARCHAR NOT NULL, 
                file_path VARCHAR NOT NULL, 
                file_type VARCHAR NOT NULL, 
                rag_type VARCHAR, 
                description VARCHAR, 
                status VARCHAR NOT NULL CHECK (status IN ('PROCESSING', 'READY', 'ERROR')), 
                created_at TIMESTAMP, 
                updated_at TIMESTAMP, 
                PRIMARY KEY (id), 
                UNIQUE (file_uuid)
            )
        """))
        
        # 2. Get column names from the original table
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'files' 
            ORDER BY ordinal_position
        """))
        columns = [row[0] for row in result]
        
        # 3. Copy data from old table to new table with explicit column mapping
        # Make sure the columns are in the correct order
        db.execute(text("""
            INSERT INTO files_new (
                id, 
                file_uuid, 
                filename, 
                original_filename, 
                file_path, 
                file_type, 
                rag_type, 
                description,
                created_at,
                updated_at,
                status
            )
            SELECT 
                id,
                file_uuid::uuid,
                filename,
                original_filename,
                file_path,
                file_type,
                rag_type,
                description,
                created_at::timestamp,
                updated_at::timestamp,
                UPPER(status) as status
            FROM files
        """))
        
        # 3. Drop foreign key constraints first
        db.execute(text("""
            ALTER TABLE processed_data 
            DROP CONSTRAINT IF EXISTS processed_data_file_id_fkey
        """))
        
        db.execute(text("""
            ALTER TABLE pdf_documents 
            DROP CONSTRAINT IF EXISTS pdf_documents_file_id_fkey
        """))
        
        db.execute(text("""
            ALTER TABLE csv_documents 
            DROP CONSTRAINT IF EXISTS csv_documents_file_id_fkey
        """))
        
        db.execute(text("""
            ALTER TABLE xlsx_documents 
            DROP CONSTRAINT IF EXISTS xlsx_documents_file_id_fkey
        """))
        
        # 4. Now drop the old table
        db.execute(text("DROP TABLE IF EXISTS files CASCADE"))
        
        # 5. Rename new table to original name
        db.execute(text("ALTER TABLE files_new RENAME TO files"))
        
        # 6. Recreate foreign key constraints
        db.execute(text("""
            ALTER TABLE processed_data
            ADD CONSTRAINT processed_data_file_id_fkey 
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        """))
        
        db.execute(text("""
            ALTER TABLE pdf_documents
            ADD CONSTRAINT pdf_documents_file_id_fkey 
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        """))
        
        db.execute(text("""
            ALTER TABLE csv_documents
            ADD CONSTRAINT csv_documents_file_id_fkey 
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        """))
        
        db.execute(text("""
            ALTER TABLE xlsx_documents
            ADD CONSTRAINT xlsx_documents_file_id_fkey 
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        """))
        
        db.commit()
        print("Successfully updated enum values to uppercase")
    except Exception as e:
        db.rollback()
        print(f"Error updating enum values: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_enum_values()
