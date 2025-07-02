import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def check_database_connection():
    print("Checking database connection...")
    
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment variables
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    print(f"Database URL: {database_url}")
    
    try:
        # Create engine and connect to database
        engine = create_engine(database_url)
        connection = engine.connect()
        
        # Test the connection
        result = connection.execute(text("SELECT version()"))
        db_version = result.scalar()
        print(f"✅ Connected to database. Version: {db_version}")
        
        # Check if users table exists
        result = connection.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
        ))
        users_table_exists = result.scalar()
        
        if users_table_exists:
            print("✅ Users table exists")
            
            # List all users
            result = connection.execute(text("SELECT id, username, email, role FROM users"))
            users = result.fetchall()
            
            if users:
                print("\nExisting users:")
                for user in users:
                    print(f"- ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Role: {user[3]}")
            else:
                print("\n❌ No users found in the database")
                print("You may need to create a user first.")
                print("\nTo create an admin user, you can run:")
                print("""
from app.database import SessionLocal
from app.models import User
from app.auth import hash_password

db = SessionLocal()

# Create admin user
admin = User(
    username="admin",
    email="admin@example.com",
    password_hash=hash_password("admin123"),
    role="admin",
    is_active=True
)

db.add(admin)
db.commit()
print("Admin user created successfully!")
                """)
        else:
            print("❌ Users table does not exist")
            print("You may need to run database migrations first.")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to database: {str(e)}")
        return False

if __name__ == "__main__":
    check_database_connection()
