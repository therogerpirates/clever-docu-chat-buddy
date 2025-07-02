import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create engine
engine = create_engine(DATABASE_URL)

# Test the connection and query
with engine.connect() as connection:
    # Check if users table exists
    result = connection.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'users'
    """))
    
    if result.fetchone():
        print("Users table exists. Checking for users...")
        
        # Count users
        result = connection.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        print(f"Found {count} users in the database.")
        
        # List first 5 users
        if count > 0:
            result = connection.execute(text("SELECT id, username, email, role FROM users LIMIT 5"))
            print("\nFirst 5 users:")
            print("-" * 80)
            for row in result:
                print(f"ID: {row[0]}, Username: {row[1]}, Email: {row[2]}, Role: {row[3]}")
    else:
        print("Users table does not exist in the database.")
