import sys
import os
from sqlalchemy import create_engine, text, and_
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the parent directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import engine, SessionLocal
from app.models import File, User, FileStatus

def main():
    """Fix file permissions and clean up database."""
    db = SessionLocal()
    
    try:
        # Get admin user
        admin = db.query(User).filter_by(username='admin').first()
        if not admin:
            print("Admin user not found!")
            return
        
        # Get all files
        files = db.query(File).all()
        print(f"Found {len(files)} files in total")
        
        # Clean up files with ERROR status
        error_files = db.query(File).filter(File.status == FileStatus.ERROR).all()
        if error_files:
            print(f"\nFound {len(error_files)} files with ERROR status")
            for file in error_files:
                print(f"- Deleting file (ID: {file.id}): {file.original_filename}")
                db.delete(file)
            db.commit()
            print("Deleted error files")
        
        # Get remaining files
        files = db.query(File).filter(File.status == FileStatus.READY).all()
        print(f"\n{len(files)} files with READY status:")
        
        # Ensure admin has access to all files
        for file in files:
            # Check if admin is already in restricted_users
            if admin not in file.restricted_users:
                file.restricted_users.append(admin)
                print(f"- Granted admin access to: {file.original_filename}")
        
        db.commit()
        print("\nPermissions updated successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Fixing file permissions...\n")
    main()
    print("\nDone!")
