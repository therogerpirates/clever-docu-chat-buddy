#!/usr/bin/env python3
"""
Test database connection and basic operations
"""

import os
import sys
from pathlib import Path
from sqlalchemy import text

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / 'app'))

def test_database_connection():
    """Test database connection and basic operations"""
    
    print("🔍 Testing Database Connection")
    print("=" * 40)
    
    try:
        # Test environment variables
        print("📋 Checking environment variables...")
        from dotenv import load_dotenv
        load_dotenv()
        
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            return False
        
        print(f"✅ DATABASE_URL found: {database_url[:50]}...")
        
        # Test database connection
        print("\n🔌 Testing database connection...")
        from app.database import engine
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Database connection successful")
        
        # Test models
        print("\n📊 Testing database models...")
        from app.models import Base, User, File, FileType, FileStatus
        
        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"📋 Found tables: {tables}")
        
        # Test creating a session
        from app.database import SessionLocal
        db = SessionLocal()
        
        try:
            # Test querying users
            users = db.query(User).all()
            print(f"👥 Found {len(users)} users in database")
            
            # Test querying files
            files = db.query(File).all()
            print(f"📁 Found {len(files)} files in database")
            
        finally:
            db.close()
        
        print("\n✅ Database test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1) 