from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import traceback
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json
from sqlalchemy.orm import Session

# Import local modules
from .llm_utils import generate_chat_response, get_groq_chat
from .database import get_db, SessionLocal
from .models import File, PDFDocument, CSVDocument, XLSXDocument, FileType, RagType, ProcessedData, PDFChunk, CSVChunk, XLSXChunk, FileStatus
from .init_db import init_db
from .utils import ensure_upload_dir, save_uploaded_file, process_file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Initialize database tables (only creates them if they don't exist)
init_db()

# CORS configuration
origins = [
    "http://localhost:8080",  # Frontend URL
    "http://127.0.0.1:8080",  # Frontend URL (alternative)
    "http://localhost:8081",  # Frontend URL (additional port)
    "http://127.0.0.1:8081",  # Frontend URL (additional port alternative)
    "http://localhost:3000",  # Alternative frontend port
    "http://127.0.0.1:3000",  # Alternative frontend port (alternative)
    "http://localhost:5173",  # Vite default port
    "http://127.0.0.1:5173",  # Vite default port (alternative)
    "http://localhost:8000",  # Backend URL
    "http://127.0.0.1:8000",  # Backend URL (alternative)
    "https://your-production-domain.com"  # Add production domain when deployed
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],  # Frontend dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight request for 10 minutes
)

# Add CORS headers to all responses
# Remove custom CORS middleware as we're using the CORSMiddleware

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/api/chat")
async def get_chat():
    """Handle GET requests to the chat endpoint (for testing)"""
    return {"status": "Chat API is running", "docs": "/docs"}

@app.options("/api/chat")
async def options_chat():
    # Handle preflight request
    return {"message": "OK"}

@app.post("/api/chat")
async def chat(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle chat requests with RAG (Retrieval-Augmented Generation) using Groq LLM.
    
    Request body should be a JSON object with:
    - messages: List of message objects with 'role' and 'content'
    - system_prompt: Optional system prompt to guide the model
    - model: Optional model name to override the default
    - use_rag: Whether to use RAG (default: True)
    - rag_limit: Number of chunks to retrieve (default: 3)
    - min_score: Minimum similarity score for RAG (default: 0.5)
    """
    try:
        # Parse request body
        body = await request.json()
        messages = body.get("messages", [])
        system_prompt = body.get("system_prompt")
        model_name = body.get("model")
        use_rag = body.get("use_rag", True)
        rag_limit = body.get("rag_limit", 3)
        min_score = body.get("min_score", 0.5)
        
        logger.info(f"Received chat request with {len(messages)} messages, use_rag={use_rag}")
        
        # Get the last user message
        user_message = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), None)
        
        # Initialize context and sources
        context = ""
        sources = []
        
        # If RAG is enabled and we have a user message
        if use_rag and user_message:
            try:
                from .rag_utils import VectorStore, generate_insights_from_chunks
                
                # Perform semantic search
                vector_store = VectorStore(db)
                relevant_chunks = await vector_store.search_semantic(
                    query=user_message,
                    limit=rag_limit,
                    min_score=min_score
                )
                
                if relevant_chunks:
                    # Generate insights using the LLM with the relevant chunks
                    insights = await generate_insights_from_chunks(
                        query=user_message,
                        chunks=relevant_chunks,
                        model_name=model_name
                    )
                    
                    # Return the insights directly
                    return JSONResponse(
                        content={
                            "response": insights["response"],
                            "model": model_name or os.getenv("LLM_MODEL", "unknown"),
                            "sources": insights["sources"],
                            "usage": {}  # Add usage info if available
                        },
                        headers={"Access-Control-Allow-Origin": "*"}
                    )
                    
            except Exception as e:
                logger.error(f"Error in RAG processing: {str(e)}", exc_info=True)
                # Continue without RAG if there's an error
        
        # If we get here, either RAG is disabled or no relevant chunks were found
        # Fall back to regular chat response
        result = await generate_chat_response(
            messages=messages,
            system_prompt=system_prompt,
            model_name=model_name
        )
        
        # Check if there was an error in the response
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
        
        # Return successful response
        response_data = {
            "response": result.get("response", "No response generated"),
            "model": result.get("model", model_name or os.getenv("LLM_MODEL", "unknown")),
            "usage": result.get("usage", {}),
            "sources": []  # No sources for non-RAG responses
        }
        
        return JSONResponse(
            content=response_data,
            headers={"Access-Control-Allow-Origin": "*"}
        )
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request body",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        error_msg = f"Error in chat endpoint: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=error_msg,
            headers={"Access-Control-Allow-Origin": "*"}
        )

@app.get("/api/upload")
@app.get("/api/upload/")
async def get_upload_info(db: Session = Depends(get_db)):
    """
    Return the list of uploaded files.
    
    Returns:
        List[Dict]: List of file objects with their details
    """
    try:
        files = db.query(File).order_by(File.created_at.desc()).all()
        return [
            {
                "id": file.id,
                "file_uuid": file.file_uuid,
                "name": file.filename,
                "original_filename": file.original_filename,
                "type": file.file_type.value,
                "description": file.description,
                "rag_type": file.rag_type.value if file.rag_type else None,
                "status": file.status.value if hasattr(file, 'status') else 'unknown',
                "upload_date": file.created_at.isoformat() if hasattr(file, 'created_at') else None,
                "size": str(file.size) if hasattr(file, 'size') else None,
                "url": f"/uploads/{file.file_path}" if hasattr(file, 'file_path') and file.file_path else None,
                "metadata": json.loads(file.metadata) if hasattr(file, 'metadata') and file.metadata else {}
            }
            for file in files
        ]
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )

@app.options("/api/upload")
@app.options("/api/upload/")
async def options_upload():
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:5173",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.post("/api/upload")
@app.post("/api/upload/")
async def upload_file(
    file: UploadFile,
    description: str = Form(...),
    rag_type: str = Form("semantic"),
    db: Session = Depends(get_db)
):
    try:
        # Validate file type and size
        if not file or not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided or file is empty"
            )
        
        # Generate a unique file UUID and save file
        file_uuid = str(uuid.uuid4())
        file_path = await save_uploaded_file(file)
        file_type = file.filename.split('.')[-1].lower()
        
        # Create database entry with initial 'processing' status
        db_file = File(
            file_uuid=file_uuid,
            filename=file.filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_type=FileType(file_type),
            description=description,
            rag_type=RagType(rag_type) if rag_type else None,
            status=FileStatus.PROCESSING
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        try:
            # Process file with retry logic
            process_result = process_file(str(file_path), file_type, description, rag_type)
            
            # Update file status to 'ready' if processing succeeds
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
            # Update file status to 'error' if processing fails
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
    """
    Handle file uploads and process them based on file type.
    
    Args:
        file: The uploaded file (PDF, CSV, or XLSX)
        description: Description of the file
        rag_type: Type of RAG to use (default: "semantic")
        
    Returns:
        dict: Status and details of the upload
    """
    logger.info(f"Received file upload request. Filename: {file.filename if file else 'None'}")
    
    try:
        logger.info(f"Received file upload request. File: {file.filename if file else 'None'}, Size: {file.size if file else 0} bytes")
        
        # Validate file type and size
        if not file or not file.filename:
            error_msg = "No file provided or file is empty"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": "error", "message": error_msg}
            )
        
        file_extension = file.filename.split(".")[-1].lower()
        logger.info(f"File extension: {file_extension}")
        
        if file_extension not in ["pdf", "csv", "xlsx"]:
            error_msg = f"Unsupported file type: {file_extension}. Supported types: PDF, CSV, XLSX"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": "error", "message": error_msg}
            )
            
        # Check file size (10MB max)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        if len(file_content) > max_size:
            error_msg = "File too large. Maximum size is 10MB"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": "error", "message": error_msg}
            )
            
        # Reset file pointer after reading
        await file.seek(0)
        
        # Ensure upload directory exists
        ensure_upload_dir()
        
        # Save the uploaded file
        try:
            file_path, stored_filename = save_uploaded_file(file, description, rag_type)
            logger.info(f"File saved to: {file_path}")
            
            # Save file metadata to database
            file_record = File(
                file_uuid=str(uuid.uuid4()),
                filename=stored_filename,
                original_filename=file.filename,
                file_path=file_path,
                file_type=FileType[file_extension.upper()],
                rag_type=RagType[rag_type.upper()] if rag_type else None,
                description=description
            )
            db.add(file_record)
            db.commit()
            db.refresh(file_record)
            
            # Process the file based on its type
            result = None
            if file_extension == 'pdf':
                from .pdf_utils import process_pdf
                result = process_pdf(file_path, file_record.id, db)
            elif file_extension == 'csv':
                from .csv_utils import process_csv_with_embeddings as process_csv
                result = process_csv(file_path, file_record.id, db)
            elif file_extension == 'xlsx':
                from .xlsx_utils import process_xlsx_with_embeddings as process_xlsx
                result = process_xlsx(file_path, file_record.id, db)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"status": "error", "message": f"Unsupported file type: {file_extension}"}
                )
            
            # No need to update processed status directly as it's not in the model
            # Status will be determined by the presence of processed data and embeddings
            pass
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "success",
                    "message": "File uploaded and processed successfully",
                    "file_path": file_path,
                    "file_type": file_extension,
                    "file_id": file_record.id,
                    "file_uuid": str(file_record.file_uuid)
                }
            )
            
        except Exception as process_error:
            logger.error(f"Error processing file: {str(process_error)}", exc_info=True)
            
            # Clean up the saved file if it exists
            if 'file_path' in locals() and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up file after processing error: {file_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up file {file_path}: {str(e)}")
            
            error_detail = {
                "status": "error",
                "message": f"Error processing file: {str(process_error)}",
                "exception_type": str(type(process_error).__name__)
            }
            
            if isinstance(process_error, HTTPException):
                if hasattr(process_error, 'detail') and isinstance(process_error.detail, dict):
                    error_detail.update(process_error.detail)
                else:
                    error_detail["message"] = str(process_error.detail) if hasattr(process_error, 'detail') else str(process_error)
                
                logger.error(f"Raising HTTPException: {error_detail}")
                raise HTTPException(
                    status_code=getattr(process_error, 'status_code', status.HTTP_500_INTERNAL_SERVER_ERROR),
                    detail=error_detail
                )
            
            logger.error(f"Unexpected error: {error_detail}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_detail
            )
            
        finally:
            try:
                db.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")
    
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions as-is
        logger.error(f"HTTP Exception: {str(http_exc.detail)}")
        raise
        
    except Exception as e:
        error_msg = f"Unexpected error processing file: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": error_msg}
        )

@app.post("/api/files/{file_id}/reprocess")
async def reprocess_file(file_id: int, db: Session = Depends(get_db)):
    """
    Reprocess a file to generate embeddings.
    
    Args:
        file_id: ID of the file to reprocess
        db: Database session
    """
    try:
        # Get file record
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Update status to processing
        file.status = 'processing'
        db.commit()
        
        try:
            # Reprocess file
            result = process_file(file.file_path, file.file_type, file.description, file.rag_type)
            
            # Update status to ready on success
            file.status = 'ready'
            db.commit()
            
            return {
                "status": "success",
                "message": "File reprocessed successfully",
                "result": result
            }
            
        except Exception as process_error:
            # Update status to error if processing fails
            file.status = 'error'
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

@app.get("/api/files/{file_id}")
async def get_file(file_id: int, db: Session = Depends(get_db)):
    """
    Get file details including current status.
    
    Args:
        file_id: ID of the file to get
        db: Database session
    """
    try:
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
            
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
            "size": os.path.getsize(file.file_path) if os.path.exists(file.file_path) else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files", response_model=List[Dict[str, Any]])
@app.get("/api/files/", response_model=List[Dict[str, Any]])
async def list_files(db: Session = Depends(get_db)):
    """
    List all uploaded files with their details.
    
    Returns:
        List[Dict]: List of file objects with their details
    """
    try:
        files = db.query(File).order_by(File.created_at.desc()).all()
        
        result = []
        for file in files:
            # Determine file size
            file_path = Path(file.file_path)
            file_size = None
            if file_path.exists():
                file_size = f"{file_path.stat().st_size / 1024:.1f} KB"
            
            # Get additional metadata based on file type
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
            
            # Get the status, defaulting to PROCESSING if not set
            status_value = file.status if file.status is not None else FileStatus.PROCESSING
            
            result.append({
                "id": file.id,
                "file_uuid": str(file.file_uuid),
                "name": file.original_filename,
                "type": file.file_type.value.lower() if file.file_type else None,
                "description": file.description or "",
                "rag_type": file.rag_type.value if file.rag_type else None,
                "upload_date": file.created_at.isoformat(),
                "status": status_value.lowercase,  # Use the lowercase property for frontend
                "size": file_size,
                "metadata": metadata
            })
            
        return result
        
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to list files")

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: int, db: Session = Depends(get_db)):
    """
    Delete an uploaded file and its associated data.
    
    Args:
        file_id: ID of the file to delete
        
    Returns:
        dict: Status of the operation
    """
    try:
        # Find the file
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete the physical file if it exists
        try:
            file_path = Path(file.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete file {file_path}: {str(e)}")
        
        # Delete the database record (cascading delete will handle related records)
        db.delete(file)
        db.commit()
        
        return {"status": "success", "message": "File deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting file: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to delete file")
