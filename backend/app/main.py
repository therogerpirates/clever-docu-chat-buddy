from fastapi import FastAPI, HTTPException, Request, UploadFile, File as FastAPIFile, Form, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import logging
import traceback
import os
import urllib.parse
import time  # Added missing import
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import json
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dotenv import load_dotenv
from jose import jwt, JWTError
import pandas as pd

# Load environment variables
load_dotenv()

# Print environment variables for debugging
print("Environment Variables:")
print(f"GROQ_API present: {'GROQ_API' in os.environ}")
print(f"GROQ_API value: {os.environ.get('GROQ_API')}")
print(f"LLM_MODEL: {os.environ.get('LLM_MODEL')}")

# Import local modules
from .llm_utils import generate_chat_response, get_groq_chat
from .database import get_db, SessionLocal
from .models import File, PDFDocument, CSVDocument, XLSXDocument, FileType, RagType, ProcessedData, PDFChunk, CSVChunk, XLSXChunk, FileStatus, User, UserRole, WebsiteDocument
from .init_db import init_db
from .utils import ensure_upload_dir, save_uploaded_file, process_file, save_file_to_db
from .website_processor import WebsiteProcessor
from .auth import (
    hash_password, verify_password, create_access_token, get_current_user,
    require_admin, require_admin_or_manager, ACCESS_TOKEN_EXPIRE_MINUTES
)
from .pdf_utils import extract_pdf_metadata, extract_pdf_content, get_embedding_with_retry as get_pdf_embedding_with_retry
from .csv_utils import get_embedding_with_retry as get_csv_embedding_with_retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Initialize database tables (only creates them if they don't exist)
init_db()

# Pydantic models for request/response
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool

class FileRestrictionRequest(BaseModel):
    user_ids: List[int]

class WebsiteUploadRequest(BaseModel):
    url: str
    description: Optional[str] = None

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add test endpoints for debugging
@app.get("/api/test-cors")
async def test_cors():
    return {"message": "CORS is working!"}

# Test upload endpoint without authentication for debugging
from fastapi import FastAPI, HTTPException, Request, UploadFile, File as FastAPIFile, Form, status, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import logging
import traceback
import os
import urllib.parse
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, BinaryIO
from datetime import datetime, timedelta
import uuid
import json
import shutil
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dotenv import load_dotenv

# ... (keep other imports and setup code)

@app.post("/api/upload/test")
async def test_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = FastAPIFile(...),
    description: str = Form("Test upload"),
    rag_type: str = Form("semantic"),
    db: Session = Depends(get_db)
):
    """Test endpoint for file upload without authentication"""
    try:
        logger.info(f"\n=== Test Upload Request ===")
        logger.info(f"Received file: {file.filename if file else 'None'}")
        logger.info(f"Description: {description}")
        logger.info(f"RAG type: {rag_type}")
        
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Ensure upload directory exists
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        # Generate a unique filename
        file_extension = Path(file.filename).suffix if file.filename else '.bin'
        unique_filename = f"test_upload_{int(time.time())}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save the file asynchronously
        try:
            # Save the file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            logger.info(f"Successfully saved file to: {file_path}")
            
            # Get file size
            file_size = file_path.stat().st_size
            
            # Process the file in the background if needed
            # background_tasks.add_task(process_file, file_path, description, rag_type, db)
            
            return {
                "status": "success",
                "message": "File uploaded successfully",
                "filename": file.filename,
                "saved_as": str(file_path),
                "size": file_size,
                "content_type": file.content_type
            }
            
        except IOError as e:
            logger.error(f"Failed to save file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
            
    except HTTPException as http_err:
        raise http_err
        
    except Exception as e:
        error_msg = f"Unexpected error during upload: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        # Return a safe error message without binary data
        raise HTTPException(status_code=500, detail="An error occurred while processing the file")

# Define backend directory to construct absolute paths
BACKEND_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BACKEND_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Authentication endpoints
@app.post("/api/auth/login", response_model=LoginResponse)
async def login(login_request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return access token."""
    try:
        # Find user by username
        user = db.query(User).filter(User.username == login_request.username).first()
        
        if not user or not verify_password(login_request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "is_active": user.is_active
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.value,
        is_active=current_user.is_active
    )

@app.get("/api/users", response_model=List[UserResponse])
async def list_users(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """List all users (Admin only)."""
    users = db.query(User).all()
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            is_active=user.is_active
        )
        for user in users
    ]

# File restriction endpoints
@app.post("/api/files/{file_id}/restrictions")
async def set_file_restrictions(
    file_id: int,
    restriction_request: FileRestrictionRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Set file access restrictions (Admin only)."""
    try:
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Clear existing restrictions
        file.restricted_users.clear()
        
        # Add new restrictions
        restricted_users = db.query(User).filter(User.id.in_(restriction_request.user_ids)).all()
        file.restricted_users.extend(restricted_users)
        
        db.commit()
        
        return {"status": "success", "message": "File restrictions updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting file restrictions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to set file restrictions")

@app.get("/api/files/{file_id}/restrictions")
async def get_file_restrictions(
    file_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get file access restrictions (Admin only)."""
    try:
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        restricted_user_ids = [user.id for user in file.restricted_users]
        
        return {
            "file_id": file_id,
            "restricted_user_ids": restricted_user_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file restrictions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get file restrictions")

def can_access_file(file: File, user: User) -> bool:
    """Check if a user can access a file based on role and restrictions."""
    # Admin can access all files
    if user.role == UserRole.ADMIN:
        return True
    
    # If file has restricted users, only allow access to those users
    if file.restricted_users:
        return user in file.restricted_users
    
    # If no restrictions, allow access to all authenticated users
    return True

# Updated existing endpoints with authentication
@app.get("/api/chat")
async def get_chat(current_user: User = Depends(get_current_user)):
    """Handle GET requests to the chat endpoint (for testing)"""
    return {"status": "Chat API is running", "docs": "/docs", "user": current_user.username}

@app.post("/api/chat")
async def chat(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handle chat requests with RAG - now with authentication."""
    try:
        # Log the start of the request
        logger.info(f"Received chat request from user {current_user.username} (ID: {current_user.id})")
        
        # Parse request body
        try:
            body = await request.json()
            messages = body.get("messages", [])
            system_prompt = body.get("system_prompt")
            model_name = body.get("model")
            use_rag = body.get("use_rag", True)
            rag_limit = body.get("rag_limit", 3)
            min_score = body.get("min_score", 0.5)
            
            # Log request details
            logger.debug(f"Request body: {json.dumps(body, indent=2)}")
            logger.info(f"Processing {len(messages)} messages with model: {model_name or 'default'}")
            
        except json.JSONDecodeError as je:
            error_msg = f"Invalid JSON in request body: {str(je)}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        except Exception as e:
            error_msg = f"Error parsing request body: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"User {current_user.username} (ID: {current_user.id}, Role: {current_user.role}) sent chat request with {len(messages)} messages")
        logger.debug(f"Chat request body: {json.dumps(body, indent=2)}")
        
        user_message = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), None)
        
        context = ""
        sources = []
        
        if use_rag and user_message:
            try:
                from .rag_utils import VectorStore, generate_insights_from_chunks
                
                logger.info(f"Starting RAG processing for user: {current_user.username}")
                
                # Search for relevant chunks with access control
                vector_store = VectorStore(db)
                logger.info(f"Searching for relevant chunks for query: {user_message}")
                
                relevant_chunks = await vector_store.search_semantic(
                    query=user_message,
                    limit=rag_limit,
                    min_score=min_score,
                    current_user=current_user
                )
                
                logger.info(f"Found {len(relevant_chunks)} relevant chunks")
                
                if relevant_chunks:
                    try:
                        logger.info("Generating insights from chunks...")
                        insights = await generate_insights_from_chunks(
                            query=user_message,
                            chunks=relevant_chunks,
                            model_name=model_name
                        )
                        
                        logger.info("Successfully generated insights from RAG")
                        
                        # Prepare response data with all required fields
                        response_data = {
                            "response": insights.get("response", "No response generated"),
                            "model": model_name or os.getenv("LLM_MODEL", "unknown"),
                            "sources": insights.get("sources", []),
                            "usage": {}
                        }
                        
                        logger.debug(f"Response data prepared: {json.dumps(response_data, indent=2)}")
                        
                        logger.debug(f"RAG response data: {response_data}")
                        
                        return JSONResponse(
                            content=response_data,
                            headers={"Access-Control-Allow-Origin": "*"}
                        )
                    except Exception as inner_e:
                        logger.error(f"Error in RAG response generation: {str(inner_e)}", exc_info=True)
                        # Fall through to non-RAG response
                else:
                    logger.info("No relevant chunks found for RAG, falling back to general response")
                    
            except Exception as e:
                logger.error(f"Error in RAG processing: {str(e)}", exc_info=True)
                # Fall back to non-RAG response
                logger.info("Falling back to general response generation with model: %s", model_name)
                response_data = await generate_chat_response(
                    messages=messages,
                    system_prompt=system_prompt,
                    model_name=model_name
                )
                
                if "error" in response_data:
                    error_msg = f"Error in chat response: {response_data['error']}"
                    logger.error(error_msg)
                    return JSONResponse(
                        status_code=500,
                        content={
                            "error": response_data["error"],
                            "response": response_data.get("response", "An error occurred"),
                            "sources": []
                        },
                        headers={"Access-Control-Allow-Origin": "*"}
                    )
                
                logger.info("Chat response generated successfully")
                return JSONResponse(
                    status_code=200,
                    content=response_data,
                    headers={"Access-Control-Allow-Origin": "*"}
                )
            
            # If we get here, RAG was attempted but no relevant chunks were found
            logger.info("No relevant chunks found in RAG, falling back to general response")
            
        # Fall through to non-RAG response generation
        logger.info("Using non-RAG response generation")
        try:
            response_data = await generate_chat_response(
                messages=messages,
                system_prompt=system_prompt,
                model_name=model_name
            )
            
            if "error" in response_data:
                error_msg = f"Error in chat response: {response_data['error']}"
                logger.error(error_msg)
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": response_data["error"],
                        "response": response_data.get("response", "An error occurred"),
                        "sources": []
                    },
                    headers={"Access-Control-Allow-Origin": "*"}
                )
                
            logger.info("Chat response generated successfully")
            return JSONResponse(
                status_code=200,
                content=response_data,
                headers={"Access-Control-Allow-Origin": "*"}
            )
            
        except Exception as e:
            logger.error(f"Error generating chat response: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Failed to generate response",
                    "message": str(e)
                }
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        error_msg = f"Unexpected error processing chat request: {str(e)}"
        logger.error(error_msg)
        logger.exception("Error details:")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred while processing your request"
            }
        )
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process chat request")
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/upload")
@app.post("/api/upload/website", response_model=dict)
async def upload_website(
    request: Request = None,
    website_request: WebsiteUploadRequest = None,
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Upload and process a website URL.
    
    This endpoint accepts a website URL, scrapes its content, and processes it
    for semantic search similar to other document types.
    """
    try:
        # Debug: Print request details
        print("\n=== DEBUG: Received upload_website request ===")
        print(f"Request method: {request.method if request else 'No request object'}")
        print(f"Request headers: {dict(request.headers) if request else 'No headers'}" if request else '')
        print(f"Request content type: {request.headers.get('content-type') if request else 'No content type'}" if request else '')
        
        # Try to get raw request body for debugging
        if request:
            try:
                body = await request.body()
                print(f"Raw request body: {body.decode()}")
            except Exception as e:
                print(f"Could not read request body: {str(e)}")
        
        # Debug: Print the parsed request
        print(f"Parsed request: {website_request}")
        
        if not website_request or not website_request.url:
            print("ERROR: No URL provided in request")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No URL provided in request"
            )
            
        url = website_request.url.strip()
        print(f"Processing URL: {url}")
        
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
            print(f"Added https:// prefix. New URL: {url}")
            
        logger.info(f"Processing website URL: {url}")
        
        # Validate URL format
        parsed_url = urllib.parse.urlparse(url)
        print(f"Parsed URL: {parsed_url}")
        
        if not parsed_url.scheme or not parsed_url.netloc:
            error_msg = "Invalid URL format. Please provide a valid URL with http:// or https://"
            print(f"ERROR: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Initialize website processor
        processor = WebsiteProcessor(db)
        print("Initialized WebsiteProcessor")
        
        # Create a file record for the website
        website_file = File(
            filename=url,
            original_filename=url,
            file_path=url,
            file_type=FileType.WEBSITE,
            status=FileStatus.PROCESSING,
            uploaded_by_id=current_user.id,
            file_metadata={"url": url}
        )
        db.add(website_file)
        db.commit()
        db.refresh(website_file)
        
        # Process the website
        print("Starting website processing...")
        result = await processor.process_website(url, website_file.id, current_user.id)
        print(f"Website processing complete. Result: {result}")
        
        response = {
            "status": "success",
            "message": "Website is being processed in the background",
            "website_id": result.get("website_id"),
            "file_id": result.get("file_id")
        }
        print(f"Returning response: {response}")
        return response
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing website {request.url}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process website: {str(e)}"
        )

@app.post("/api/upload/website", response_model=dict)
async def process_website_url(
    request: Request,
    url: str = Form(..., description="Website URL to process"),
    description: str = Form(..., description="Description of the website content"),
    rag_type: str = Form("semantic", description="Type of RAG processing to apply"),
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Process a website URL - Admin and Manager only.
    
    This endpoint handles website URL processing, including:
    1. URL validation
    2. Web scraping
    3. Text extraction and cleaning
    4. Chunking
    5. Embedding generation
    6. Storage in vector database
    """
    logger.info(f"Website processing request received for URL: {url}")
    
    try:
        # Validate URL
        parsed_url = urllib.parse.urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            error_msg = f"Invalid URL format: {url}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Ensure URL has a scheme
        if not parsed_url.scheme:
            url = f"https://{url}"
            parsed_url = urllib.parse.urlparse(url)
        
        # Create a file record for the website first
        website_file = File(
            filename=f"website_{int(datetime.utcnow().timestamp())}",
            original_filename=url,
            file_path=url,
            file_type=FileType.WEBSITE,
            rag_type=RagType(rag_type) if rag_type else RagType.SEMANTIC,
            status=FileStatus.PROCESSING,
            uploaded_by_id=current_user.id,
            file_metadata={"url": url, "description": description}
        )
        db.add(website_file)
        db.commit()
        db.refresh(website_file)
        
        # Create a database entry for the website
        db_website = WebsiteDocument(
            file_id=website_file.id,
            uploaded_by_id=current_user.id,
            url=url,
            domain=parsed_url.netloc,
            description=description,
            rag_type=RagType(rag_type) if rag_type else RagType.SEMANTIC,
            status="processing",
            document_metadata={"url": url, "description": description}
        )
        
        db.add(db_website)
        db.commit()
        db.refresh(db_website)
        
        # Process the website asynchronously using WebsiteProcessor
        website_processor = WebsiteProcessor(db)
        asyncio.create_task(website_processor.process_website(
            url=url,
            file_id=website_file.id,
            current_user_id=current_user.id
        ))
        
        return {
            "status": "processing",
            "message": "Website is being processed",
            "website_id": db_website.id,
            "file_id": website_file.id,
            "url": db_website.url
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        error_msg = f"Error processing website: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        
        # Update website status to failed
        if 'db_website' in locals():
            db_website.status = "failed"
            db_website.error_message = str(e)
            db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@app.post("/api/upload/")
async def get_upload_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the list of uploaded files."""
    # Redirect to list_files with authentication
    return await list_files(current_user, db)

@app.options("/api/upload")
async def options_upload():
    response = JSONResponse(content={"message": "OK"})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

@app.options("/api/chat")
async def options_chat():
    return {"message": "OK"}

@app.post("/api/upload/file", response_model=dict)
@app.options("/api/upload/file")  # Add OPTIONS handler for this endpoint
async def upload_file(
    request: Request,
    file: UploadFile = None,  # Make file optional for OPTIONS
    description: str = Form(None),  # Make description optional for OPTIONS
    rag_type: str = Form("semantic"),  # Default value for OPTIONS
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    # Log the request method and headers for debugging
    logger.info(f"\n=== New Upload Request ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request headers: {dict(request.headers)}")
    
    # Handle OPTIONS preflight request
    if request.method == "OPTIONS":
        logger.info("Handling OPTIONS preflight request")
        response = JSONResponse(content={"message": "CORS preflight successful"})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
        
    # For actual POST requests, ensure required fields are present
    if file is None or file.filename == '':
        error_msg = "No file provided or empty filename"
        logger.error(error_msg)
        raise HTTPException(
            status_code=400, 
            detail=error_msg,
            headers={"Access-Control-Allow-Origin": "*"}
        )
    
    logger.info(f"Processing file: {file.filename}")
    logger.info(f"Content type: {file.content_type}")
    logger.info(f"Description: {description}")
    logger.info(f"RAG type: {rag_type}")
    logger.info(f"Current user: {current_user.username} (ID: {current_user.id})")
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
            
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.pdf', '.csv', '.xlsx']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file_extension}"
            )
        
        # Process the file
        file_content = await file.read()
        
        # Create uploads directory if it doesn't exist
        os.makedirs("uploads", exist_ok=True)
        
        # Generate a unique filename to prevent collisions
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join("uploads", unique_filename)
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Determine file type for processing
        file_type = None
        if file_extension == '.pdf':
            file_type = 'pdf'
        elif file_extension == '.csv':
            file_type = 'csv'
        elif file_extension in ['.xlsx', '.xls']:
            file_type = 'xlsx'
        elif file_extension == '.txt':
            file_type = 'txt'
        
        # Process the file using the utils function
        from .utils import process_file
        result = process_file(
            file_path=file_path,
            file_type=file_type,
            description=description or "",
            rag_type=rag_type,
            uploaded_by_id=current_user.id,
            original_filename=file.filename
        )
        
        # PDF processing
        if file_extension == '.pdf':
            # Extract metadata and content
            metadata = extract_pdf_metadata(str(file_path))
            pages = extract_pdf_content(str(file_path))
            # Optionally, generate embeddings for each page
            embeddings = []
            for page in pages:
                try:
                    embedding = get_pdf_embedding_with_retry(page['content'])
                    embeddings.append({
                        "page_number": page['page_number'],
                        "embedding": embedding
                    })
                except Exception as e:
                    embeddings.append({
                        "page_number": page['page_number'],
                        "embedding": None,
                        "error": str(e)
                    })
            return {
                "status": "success",
                "message": "PDF processed successfully",
                "filename": file.filename,
                "metadata": metadata,
                "pages": pages,
                "embeddings": embeddings,
            }

        # CSV processing (use test_csv_processing.py logic)
        if file_extension == '.csv':
            df = pd.read_csv(str(file_path))
            results = []
            for idx, row in df.iterrows():
                row_dict = row.to_dict()
                content_str = json.dumps(row_dict, ensure_ascii=False)
                try:
                    embedding = get_csv_embedding_with_retry(content_str)
                    results.append({
                        "row_number": idx + 1,
                        "content": content_str,
                        "embedding": embedding
                    })
                except Exception as e:
                    results.append({
                        "row_number": idx + 1,
                        "content": content_str,
                        "embedding": None,
                        "error": str(e)
                    })
            return {
                "status": "success",
                "message": "CSV processed successfully",
                "filename": file.filename,
                "columns": list(df.columns),
                "rows": results,
            }

        # XLSX: (optional, similar logic can be added)
        return {
            "status": "success",
            "message": "File uploaded and processed (non-PDF/CSV)",
            "filename": file.filename,
        }
            
    except HTTPException as he:
        raise he
    except Exception as e:
        error_msg = f"Error processing file: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@app.get("/api/files", response_model=List[Dict[str, Any]])
@app.get("/api/files/", response_model=List[Dict[str, Any]])
async def list_files(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List files accessible to the current user."""
    try:
        # Get all files
        files = db.query(File).order_by(File.created_at.desc()).all()
        
        # Filter files based on user access
        accessible_files = [file for file in files if can_access_file(file, current_user)]
        
        result = []
        for file in accessible_files:
            file_path = Path(file.file_path)
            file_size = None
            if file_path.exists():
                file_size = f"{file_path.stat().st_size / 1024:.1f} KB"
            
            metadata = {}
            if file.file_type == FileType.PDF and file.pdf_document:
                metadata = {
                    "page_count": file.pdf_document.page_count,
                    "author": file.pdf_document.author,
                    "title": file.pdf_document.title
                }
            elif file.file_type == FileType.CSV and file.csv_document:
                metadata = {
                    "row_count": file.csv_document.row_count,
                    "column_count": file.csv_document.column_count
                }
            elif file.file_type == FileType.XLSX and file.xlsx_document:
                metadata = {
                    "sheet_count": file.xlsx_document.sheet_count,
                    "row_count": file.xlsx_document.row_count,
                    "column_count": file.xlsx_document.column_count
                }
            
            status_value = file.status if file.status is not None else FileStatus.PROCESSING
            
            # Check if file has any restrictions
            has_restrictions = len(file.restricted_users) > 0
            
            result.append({
                "id": file.id,
                "file_uuid": str(file.file_uuid),
                "name": file.original_filename,
                "type": file.file_type.value.lower() if file.file_type else None,
                "description": file.description or "",
                "rag_type": file.rag_type.value if file.rag_type else None,
                "upload_date": file.created_at.isoformat(),
                "status": status_value.value.lower(),
                "size": file_size,
                "metadata": metadata,
                "uploaded_by": file.uploaded_by.username if file.uploaded_by else None,
                "can_edit": current_user.role == UserRole.ADMIN or file.uploaded_by_id == current_user.id,
                "is_restricted": has_restrictions,
                "restricted_users": [user.username for user in file.restricted_users] if current_user.role == UserRole.ADMIN else []
            })
            
        return result
        
    except Exception as e:
        import traceback
        error_msg = f"Error listing files: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        # Return more detailed error for debugging
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Failed to list files",
                "details": str(e),
                "type": type(e).__name__
            }
        )

@app.delete("/api/files/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a file - Admin or file owner only."""
    try:
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check permissions: Admin or file owner can delete
        if current_user.role != UserRole.ADMIN and file.uploaded_by_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Only admins or file owners can delete files."
            )
        
        # Delete the physical file if it exists
        try:
            file_path = Path(file.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete file {file_path}: {str(e)}")
        
        db.delete(file)
        db.commit()
        
        return {"status": "success", "message": "File deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete file")

@app.get("/api/files/{file_id}")
async def get_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file details including current status."""
    try:
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check access permissions
        if not can_access_file(file, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this file"
            )
            
        status_value = file.status.value if file.status else FileStatus.PROCESSING.value
        status_str = status_value.lower()
        
        return {
            "id": file.id,
            "file_uuid": file.file_uuid,
            "name": file.filename,
            "type": file.file_type,
            "description": file.description,
            "rag_type": file.rag_type,
            "status": status_str,
            "upload_date": file.created_at,
            "size": os.path.getsize(file.file_path) if os.path.exists(file.file_path) else None,
            "uploaded_by": file.uploaded_by.username if file.uploaded_by else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/{file_id}/reprocess")
async def reprocess_file(
    file_id: int,
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """Reprocess a file to generate embeddings - Admin and Manager only."""
    try:
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check permissions: Admin or file owner can reprocess
        if current_user.role != UserRole.ADMIN and file.uploaded_by_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Only admins or file owners can reprocess files."
            )
        
        file.status = FileStatus.PROCESSING
        db.commit()
        
        try:
            result = process_file(file.file_path, file.file_type.value, file.description, file.rag_type.value if file.rag_type else None)
            file.status = FileStatus.READY
            db.commit()
            
            return {
                "status": "success",
                "message": "File reprocessed successfully",
                "result": result
            }
            
        except Exception as process_error:
            file.status = FileStatus.ERROR
            db.commit()
            logger.error(f"Error reprocessing file {file_id}: {str(process_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error reprocessing file: {str(process_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reprocess_file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/upload")
@app.get("/api/upload/")
async def get_upload_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the list of uploaded files."""
    # Redirect to list_files with authentication
    return await list_files(current_user, db)

@app.options("/api/upload")
@app.options("/api/upload/")
async def options_upload():
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:5173",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.options("/api/chat")
async def options_chat():
    return {"message": "OK"}
