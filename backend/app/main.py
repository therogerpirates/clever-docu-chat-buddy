
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import traceback
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import json
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Import local modules
from .llm_utils import generate_chat_response, get_groq_chat
from .database import get_db, SessionLocal
from .models import File, PDFDocument, CSVDocument, XLSXDocument, FileType, RagType, ProcessedData, PDFChunk, CSVChunk, XLSXChunk, FileStatus, User, UserRole
from .init_db import init_db
from .utils import ensure_upload_dir, save_uploaded_file, process_file
from .auth import (
    hash_password, verify_password, create_access_token, get_current_user,
    require_admin, require_admin_or_manager, ACCESS_TOKEN_EXPIRE_MINUTES
)

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

# CORS configuration
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://your-production-domain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

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
    
    # If user is in restricted list, deny access
    if user in file.restricted_users:
        return False
    
    # Manager and Employee can access files if not restricted
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
        body = await request.json()
        messages = body.get("messages", [])
        system_prompt = body.get("system_prompt")
        model_name = body.get("model")
        use_rag = body.get("use_rag", True)
        rag_limit = body.get("rag_limit", 3)
        min_score = body.get("min_score", 0.5)
        
        logger.info(f"User {current_user.username} sent chat request with {len(messages)} messages")
        
        user_message = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), None)
        
        context = ""
        sources = []
        
        if use_rag and user_message:
            try:
                from .rag_utils import VectorStore, generate_insights_from_chunks
                
                # Filter chunks based on file access permissions
                vector_store = VectorStore(db)
                relevant_chunks = await vector_store.search_semantic(
                    query=user_message,
                    limit=rag_limit,
                    min_score=min_score
                )
                
                # Filter chunks based on user's file access permissions
                accessible_chunks = []
                for chunk in relevant_chunks:
                    if hasattr(chunk, 'document') and hasattr(chunk.document, 'file'):
                        if can_access_file(chunk.document.file, current_user):
                            accessible_chunks.append(chunk)
                
                if accessible_chunks:
                    insights = await generate_insights_from_chunks(
                        query=user_message,
                        chunks=accessible_chunks,
                        model_name=model_name
                    )
                    
                    return JSONResponse(
                        content={
                            "response": insights["response"],
                            "model": model_name or os.getenv("LLM_MODEL", "unknown"),
                            "sources": insights["sources"],
                            "usage": {}
                        },
                        headers={"Access-Control-Allow-Origin": "*"}
                    )
                    
            except Exception as e:
                logger.error(f"Error in RAG processing: {str(e)}", exc_info=True)
        
        result = await generate_chat_response(
            messages=messages,
            system_prompt=system_prompt,
            model_name=model_name
        )
        
        if "error" in result:
            logger.error(f"Error in chat response: {result['error']}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": result["error"],
                    "response": result.get("response", "An error occurred"),
                    "sources": []
                },
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        response_data = {
            "response": result.get("response", "No response generated"),
            "model": result.get("model", model_name or os.getenv("LLM_MODEL", "unknown")),
            "usage": result.get("usage", {}),
            "sources": []
        }
        
        return JSONResponse(
            content=response_data,
            headers={"Access-Control-Allow-Origin": "*"}
        )
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except Exception as e:
        error_msg = f"Error in chat endpoint: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/upload")
@app.post("/api/upload/")
async def upload_file(
    file: UploadFile,
    description: str = Form(...),
    rag_type: str = Form("semantic"),
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """Upload file - Admin and Manager only."""
    try:
        if not file or not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided or file is empty"
            )
        
        file_uuid = str(uuid.uuid4())
        file_path = await save_uploaded_file(file)
        file_type = file.filename.split('.')[-1].lower()
        
        db_file = File(
            file_uuid=file_uuid,
            filename=file.filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_type=FileType(file_type),
            description=description,
            rag_type=RagType(rag_type) if rag_type else None,
            status=FileStatus.PROCESSING,
            uploaded_by_id=current_user.id
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        try:
            process_result = process_file(str(file_path), file_type, description, rag_type)
            db_file.status = FileStatus.READY
            db.commit()
            
            return {
                "status": "success",
                "message": "File uploaded and processed successfully",
                "file_id": db_file.id,
                "file_uuid": file_uuid,
                "process_result": process_result
            }
            
        except Exception as process_error:
            db_file.status = FileStatus.ERROR
            db.commit()
            logger.error(f"Error processing file: {str(process_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing file: {str(process_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
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
            
            # Check if user has restrictions on this file
            is_restricted = current_user in file.restricted_users
            
            result.append({
                "id": file.id,
                "file_uuid": str(file.file_uuid),
                "name": file.original_filename,
                "type": file.file_type.value.lower() if file.file_type else None,
                "description": file.description or "",
                "rag_type": file.rag_type.value if file.rag_type else None,
                "upload_date": file.created_at.isoformat(),
                "status": status_value.lowercase,
                "size": file_size,
                "metadata": metadata,
                "uploaded_by": file.uploaded_by.username if file.uploaded_by else None,
                "can_edit": current_user.role == UserRole.ADMIN or file.uploaded_by_id == current_user.id,
                "is_restricted": is_restricted,
                "restricted_users": [user.username for user in file.restricted_users] if current_user.role == UserRole.ADMIN else []
            })
            
        return result
        
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list files")

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
