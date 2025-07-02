from jose import jwt, JWTError
import bcrypt
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, UserRole
import os

# Configure logging
logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "your-secret-key-change-this-in-production":
    error_msg = "JWT_SECRET_KEY is not set or is set to the default insecure value."
    # In a real production environment, you would want to raise an error and stop the application
    # For this example, we will log a critical error.
    logger.critical(error_msg)
    # To enforce this, you might uncomment the following line:
    # raise ValueError(error_msg)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.
    
    Args:
        data: Dictionary containing the token claims (e.g., user ID, scopes)
        expires_delta: Optional timedelta for token expiration
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    
    # Set expiration time
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add standard claims
    to_encode.update({
        "exp": expire,
        "iat": now,  # Issued at
        "nbf": now,  # Not before
        "iss": "clever-docu-chat-buddy",  # Issuer
        "type": "access"  # Token type
    })
    
    # Create the token
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        raise ValueError(f"Failed to create access token: {str(e)}")

def verify_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        # Verify the token with the secret key
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}"
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current user from the JWT token.
    
    Args:
        credentials: HTTP Authorization credentials containing the JWT token
        db: Database session
        
    Returns:
        User: The authenticated user
        
    Raises:
        HTTPException: If authentication fails or user is not found
    """
    try:
        # Extract and verify the token
        token = credentials.credentials
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authentication token provided"
            )
        
        # Verify the token
        try:
            payload = verify_token(token)
        except HTTPException as e:
            logger.error(f"Token verification failed: {str(e.detail)}")
            raise
            
        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            logger.error("No user ID (sub) in token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User not found with ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Check if user is active
        if not user.is_active:
            logger.warning(f"Inactive user attempted login: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
            
        logger.debug(f"Authenticated user: {user.username} (ID: {user.id})")
        return user
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )

def require_role(required_roles: list[UserRole]):
    """Decorator to require specific roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker

# Role-based dependencies
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def require_admin_or_manager(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Manager access required"
        )
    return current_user
