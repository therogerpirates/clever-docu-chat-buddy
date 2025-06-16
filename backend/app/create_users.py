
import logging
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Base, User, UserRole
from .auth import hash_password

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_default_users():
    """Create default users for the system."""
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        
        db = SessionLocal()
        
        # Check if users already exist
        existing_users = db.query(User).count()
        if existing_users > 0:
            logger.info("Users already exist in the database. Skipping user creation.")
            return
        
        # Create default users
        users_data = [
            {
                "username": "admin",
                "email": "admin@company.com",
                "password": "admin123",
                "role": UserRole.ADMIN
            },
            {
                "username": "manager",
                "email": "manager@company.com",
                "password": "manager123",
                "role": UserRole.MANAGER
            },
            {
                "username": "employee",
                "email": "employee@company.com",
                "password": "employee123",
                "role": UserRole.EMPLOYEE
            }
        ]
        
        created_users = []
        for user_data in users_data:
            # Hash the password
            hashed_password = hash_password(user_data["password"])
            
            # Create user
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=hashed_password,
                role=user_data["role"]
            )
            
            db.add(user)
            created_users.append(user_data)
        
        db.commit()
        
        logger.info("Successfully created default users:")
        for user in created_users:
            logger.info(f"  - {user['username']} ({user['role'].value}) - {user['email']}")
            logger.info(f"    Password: {user['password']}")
        
        db.close()
        
    except Exception as e:
        logger.error(f"Error creating default users: {str(e)}")
        raise

if __name__ == "__main__":
    create_default_users()
