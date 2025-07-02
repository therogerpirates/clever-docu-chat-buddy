import logging
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from sqlalchemy.orm import Session, joinedload
import numpy as np
from .models import PDFChunk, CSVChunk, XLSXChunk, File, PDFDocument, CSVDocument, XLSXDocument, WebsiteChunk, WebsiteDocument
from .llm_utils import get_embedding, get_groq_chat
from sqlalchemy import or_

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, db: Session):
        self.db = db

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
            
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return float(dot_product / (norm_a * norm_b))

    def _get_chunk_info(self, chunk: Any) -> Tuple[str, str, str]:
        """Extract common chunk information."""
        if isinstance(chunk, PDFChunk):
            return f"Page {chunk.page_number}", "PDF", chunk.document.file.original_filename
        elif isinstance(chunk, (CSVChunk, XLSXChunk)):
            source = f"Row {chunk.row_number}"
            if hasattr(chunk, 'sheet_name'):
                source = f"{chunk.sheet_name}, {source}"
            file_type = "XLSX" if isinstance(chunk, XLSXChunk) else "CSV"
            return source, file_type, chunk.document.file.original_filename
        return "", "", ""

    async def search_semantic(
        self, 
        query: str, 
        limit: int = 5,
        min_score: float = 0.5,
        file_type: Optional[str] = None,
        current_user: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search across all document chunks using stored embeddings.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            min_score: Minimum similarity score (0-1)
            file_type: Optional file type filter ('pdf', 'csv', 'xlsx')
            current_user: The current user for access control
            
        Returns:
            List of dictionaries containing chunk information and similarity scores
        """
        try:
            logger.info(f"Starting semantic search for query: {query}")
            if current_user:
                logger.info(f"Current user: {current_user.username} (ID: {current_user.id}, Role: {current_user.role})")
            else:
                logger.info("No current user provided, applying admin-level access")
            
            # Get query embedding
            query_embedding = await get_embedding(query)
            if not query_embedding:
                logger.error("Failed to get query embedding")
                return []
                
            results = []
            
            # Search in PDF chunks
            if file_type is None or file_type.lower() == 'pdf':
                logger.info("Searching in PDF chunks...")
                
                # First, get all PDF chunks with their document and file relationships
                base_query = self.db.query(PDFChunk).options(
                    joinedload(PDFChunk.document).joinedload(PDFDocument.file)
                )
                
                # Apply access control based on user role
                if current_user and current_user.role != 'admin':
                    logger.info(f"Applying access control for user {current_user.username} (ID: {current_user.id})")
                    
                    # Get files that are either not restricted or restricted to this user
                    accessible_files = self.db.query(File).filter(
                        or_(
                            File.restricted_users.any(id=current_user.id),
                            ~File.restricted_users.any()  # No restrictions
                        )
                    ).subquery()
                    
                    # Get PDF documents for accessible files
                    accessible_docs = self.db.query(PDFDocument).join(
                        accessible_files, 
                        accessible_files.c.id == PDFDocument.file_id
                    ).subquery()
                    
                    # Get chunks for accessible documents
                    query = base_query.join(
                        accessible_docs,
                        PDFChunk.document_id == accessible_docs.c.id
                    )
                    
                    logger.debug(f"Access control query for user {current_user.id} applied")
                else:
                    # Admin or no user - get all chunks
                    query = base_query
                
                # Execute the query
                pdf_chunks = query.all()
                logger.info(f"Found {len(pdf_chunks)} PDF chunks after access control")
                
                # Process chunks and calculate similarities
                for chunk in pdf_chunks:
                    try:
                        if not chunk.embedding:
                            logger.debug(f"Skipping chunk {chunk.id} - no embedding")
                            continue
                            
                        # Convert JSON string to list if needed
                        chunk_embedding = chunk.embedding
                        if isinstance(chunk_embedding, str):
                            try:
                                chunk_embedding = json.loads(chunk_embedding)
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing embedding for chunk {chunk.id}: {e}")
                                continue
                            
                        # Calculate similarity
                        similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                        logger.debug(f"Chunk {chunk.id} similarity: {similarity:.4f}")
                        
                        if similarity >= min_score:
                            results.append({
                                'content': chunk.content,
                                'score': similarity,
                                'source': f"Page {chunk.page_number}",
                                'type': 'PDF',
                                'filename': chunk.document.file.original_filename,
                                'chunk_id': chunk.id,
                                'document_id': chunk.document_id,
                                'file': chunk.document.file  # Include file for access control
                            })
                    except Exception as e:
                        logger.error(f"Error processing PDF chunk {chunk.id}: {str(e)}")
                        continue
            
            # Search in CSV chunks
            if file_type is None or file_type.lower() == 'csv':
                logger.info("Searching in CSV chunks...")
                
                # Base query to get all CSV chunks with their relationships
                base_query = self.db.query(CSVChunk).options(
                    joinedload(CSVChunk.document).joinedload(CSVDocument.file)
                )
                
                # Apply access control based on user role
                if current_user and current_user.role != 'admin':
                    logger.info(f"Applying access control for user {current_user.username} in CSV search")
                    
                    # Get files that are either not restricted or restricted to this user
                    accessible_files = self.db.query(File).filter(
                        or_(
                            File.restricted_users.any(id=current_user.id),
                            ~File.restricted_users.any()  # No restrictions
                        )
                    ).subquery()
                    
                    # Get CSV documents for accessible files
                    accessible_docs = self.db.query(CSVDocument).join(
                        accessible_files, 
                        accessible_files.c.id == CSVDocument.file_id
                    ).subquery()
                    
                    # Get chunks for accessible documents
                    query = base_query.join(
                        accessible_docs,
                        CSVChunk.document_id == accessible_docs.c.id
                    )
                    
                    logger.debug(f"CSV access control query for user {current_user.id} applied")
                else:
                    # Admin or no user - get all chunks
                    query = base_query
                
                # Execute the query
                csv_chunks = query.all()
                logger.info(f"Found {len(csv_chunks)} CSV chunks after access control")
                
                for chunk in csv_chunks:
                    try:
                        if not chunk.embedding:
                            logger.debug(f"Skipping CSV chunk {chunk.id} - no embedding")
                            continue
                            
                        chunk_embedding = chunk.embedding
                        if isinstance(chunk_embedding, str):
                            try:
                                chunk_embedding = json.loads(chunk_embedding)
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing embedding for CSV chunk {chunk.id}: {e}")
                                continue
                            
                        similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                        logger.debug(f"CSV Chunk {chunk.id} similarity: {similarity:.4f}")
                        
                        if similarity >= min_score:
                            results.append({
                                'content': chunk.content,
                                'score': similarity,
                                'source': f"Row {chunk.row_number}",
                                'type': 'CSV',
                                'filename': chunk.document.file.original_filename,
                                'chunk_id': chunk.id,
                                'document_id': chunk.document_id,
                                'file': chunk.document.file  # Include file for access control
                            })
                    except Exception as e:
                        logger.error(f"Error processing CSV chunk {chunk.id}: {str(e)}")
                        continue
            
            # Search in XLSX chunks
            if file_type is None or file_type.lower() == 'xlsx':
                logger.info("Searching in XLSX chunks...")
                
                # Base query to get all XLSX chunks with their relationships
                base_query = self.db.query(XLSXChunk).options(
                    joinedload(XLSXChunk.document).joinedload(XLSXDocument.file)
                )
                
                # Apply access control based on user role
                if current_user and current_user.role != 'admin':
                    logger.info(f"Applying access control for user {current_user.username} in XLSX search")
                    
                    # Get files that are either not restricted or restricted to this user
                    accessible_files = self.db.query(File).filter(
                        or_(
                            File.restricted_users.any(id=current_user.id),
                            ~File.restricted_users.any()  # No restrictions
                        )
                    ).subquery()
                    
                    # Get XLSX documents for accessible files
                    accessible_docs = self.db.query(XLSXDocument).join(
                        accessible_files, 
                        accessible_files.c.id == XLSXDocument.file_id
                    ).subquery()
                    
                    # Get chunks for accessible documents
                    query = base_query.join(
                        accessible_docs,
                        XLSXChunk.document_id == accessible_docs.c.id
                    )
                    
                    logger.debug(f"XLSX access control query for user {current_user.id} applied")
                else:
                    # Admin or no user - get all chunks
                    query = base_query
                
                # Execute the query
                xlsx_chunks = query.all()
                logger.info(f"Found {len(xlsx_chunks)} XLSX chunks after access control")
                
                for chunk in xlsx_chunks:
                    try:
                        if not chunk.embedding:
                            logger.debug(f"Skipping XLSX chunk {chunk.id} - no embedding")
                            continue
                            
                        chunk_embedding = chunk.embedding
                        if isinstance(chunk_embedding, str):
                            try:
                                chunk_embedding = json.loads(chunk_embedding)
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing embedding for XLSX chunk {chunk.id}: {e}")
                                continue
                            
                        similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                        logger.debug(f"XLSX Chunk {chunk.id} similarity: {similarity:.4f}")
                        
                        if similarity >= min_score:
                            results.append({
                                'content': chunk.content,
                                'score': similarity,
                                'source': f"Sheet '{chunk.sheet_name}', Row {chunk.row_number}",
                                'type': 'XLSX',
                                'filename': chunk.document.file.original_filename,
                                'chunk_id': chunk.id,
                                'document_id': chunk.document_id,
                                'file': chunk.document.file  # Include file for access control
                            })
                    except Exception as e:
                        logger.error(f"Error processing XLSX chunk {chunk.id}: {str(e)}")
                        continue
            
            # Search in Website chunks
            if file_type is None or file_type.lower() == 'website':
                logger.info("Searching in Website chunks...")

                # Base query to get all Website chunks with their relationships
                base_query = self.db.query(WebsiteChunk).options(
                    joinedload(WebsiteChunk.document).joinedload(WebsiteDocument.file)
                )

                # Apply access control based on user role
                if current_user and current_user.role != 'admin':
                    logger.info(f"Applying access control for user {current_user.username} in Website search")
                    accessible_files = self.db.query(File).filter(
                        or_(
                            File.restricted_users.any(id=current_user.id),
                            ~File.restricted_users.any()  # No restrictions
                        )
                    ).subquery()
                    accessible_docs = self.db.query(WebsiteDocument).join(
                        accessible_files,
                        accessible_files.c.id == WebsiteDocument.file_id
                    ).subquery()
                    query = base_query.join(
                        accessible_docs,
                        WebsiteChunk.document_id == accessible_docs.c.id
                    )
                    logger.debug(f"Website access control query for user {current_user.id} applied")
                else:
                    query = base_query

                website_chunks = query.all()
                logger.info(f"Found {len(website_chunks)} Website chunks after access control")

                for chunk in website_chunks:
                    try:
                        if not chunk.embedding:
                            logger.debug(f"Skipping Website chunk {chunk.id} - no embedding")
                            continue
                        chunk_embedding = chunk.embedding
                        if isinstance(chunk_embedding, str):
                            try:
                                chunk_embedding = json.loads(chunk_embedding)
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing embedding for Website chunk {chunk.id}: {e}")
                                continue
                        similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                        logger.info(f"Website Chunk {chunk.id} similarity: {similarity:.4f} (min_score={min_score})")
                        if similarity >= min_score:
                            # Use URL as filename, and chunk index as source
                            results.append({
                                'content': chunk.content,
                                'score': similarity,
                                'source': f"Chunk {chunk.chunk_index}",
                                'type': 'WEBSITE',
                                'filename': chunk.document.file.original_filename if chunk.document and chunk.document.file else (chunk.document.url if chunk.document else 'Unknown'),
                                'chunk_id': chunk.id,
                                'document_id': chunk.document_id,
                                'file': chunk.document.file if chunk.document and chunk.document.file else None
                            })
                    except Exception as e:
                        logger.error(f"Error processing Website chunk {chunk.id}: {str(e)}")
                        continue
            
            # Sort results by score in descending order
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # Limit results
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return []

def format_context(chunks: List[Dict[str, Any]]) -> str:
    """Format search results into a context string for the LLM.
    
    Args:
        chunks: List of document chunks with content and metadata
        
    Returns:
        Formatted context string with document information
    """
    if not chunks:
        return "No relevant documents found."
    
    # Sort chunks by score in descending order
    sorted_chunks = sorted(chunks, key=lambda x: x.get('score', 0), reverse=True)
    
    context_parts = [
        "I found the following relevant information in the documents:",
        "=" * 80
    ]
    
    for i, chunk in enumerate(sorted_chunks, 1):
        try:
            # Clean up the content
            content = chunk.get('content', '').strip()
            if not content:
                continue
                
            # Truncate very long content
            max_length = 1500
            if len(content) > max_length:
                content = content[:max_length].rsplit(' ', 1)[0] + "... [content truncated]"
                
            # Format the chunk
            context_parts.extend([
                f"\n--- DOCUMENT {i} (Relevance: {chunk.get('score', 0):.2f}) ---",
                f"File: {chunk.get('filename', 'Unknown')}",
                f"Type: {chunk.get('type', 'N/A')}",
                f"Location: {chunk.get('source', 'N/A')}",
                "\nContent:",
                content,
                "\n" + "-" * 80
            ])
        except Exception as e:
            logger.error(f"Error formatting chunk {i}: {str(e)}")
            continue
    
    # Add instructions for the LLM
    context_parts.extend([
        "\nINSTRUCTIONS:",
        "1. Use the above documents to answer the user's question.",
        "2. Be specific and reference the source documents when possible.",
        "3. If the answer isn't in the documents, say so clearly.",
        "4. Include a 'SOURCES:' section at the end listing all referenced documents.",
        "5. Keep your response concise and to the point."
    ])
    
    return "\n".join(str(part) for part in context_parts)

async def generate_insights_from_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate insights from retrieved chunks using the LLM.
    
    Args:
        query: The user's query
        chunks: List of relevant chunks with content and metadata
        model_name: Optional model name to use
        
    Returns:
        Dict containing the response and sources
    """
    try:
        if not chunks:
            return {
                "response": "I couldn't find any relevant information to answer your question based on the available documents.",
                "sources": []
            }
            
        logger.info(f"Generating insights for query: {query}")
        logger.info(f"Using {len(chunks)} chunks as context")
        
        # Format the chunks into a context string with clear separation
        context = format_context(chunks)
        
        # Create a more detailed system prompt
        system_prompt = """You are an expert AI assistant that provides accurate, detailed answers based on the provided documents. 
        Follow these guidelines:
        1. Base your answer STRICTLY on the provided context
        2. Be concise but thorough
        3. If the context doesn't contain the answer, say so explicitly
        4. Include specific details and numbers when available
        5. End your response with a 'SOURCES:' section listing the document references
        
        Context documents:
        {context}"""
        
        # Create a user message that clearly states the task
        user_message = f"""Question: {query}
        
        Instructions:
        1. Provide a clear, well-structured answer
        2. Include specific details and examples from the context
        3. If the answer requires combining information from multiple documents, synthesize them coherently
        4. End with a 'SOURCES:' section listing the document references in the format:
           SOURCES:
           - [Document Name] ([Location/Page])"""
        
        # Get the chat model
        logger.info(f"Initializing chat model: {model_name or 'default'}")
        chat = await get_groq_chat(model_name=model_name)
        
        # Generate the response
        logger.info("Generating response...")
        
        # Format messages for the chat model
        from langchain_core.messages import SystemMessage, HumanMessage
        
        messages = [
            SystemMessage(content=system_prompt.format(context=context)),
            HumanMessage(content=user_message)
        ]
        
        # Generate the response
        result = await chat.agenerate([messages])
        
        # Extract the response text
        if hasattr(result, 'generations') and result.generations and len(result.generations) > 0 and len(result.generations[0]) > 0:
            response_text = result.generations[0][0].text
        else:
            logger.error(f"Unexpected response format from chat model: {result}")
            response_text = "I'm sorry, I encountered an error generating a response. Please try again later."
        logger.info("Response generated successfully")
        
        # Extract and format sources from the chunks
        sources = []
        seen_sources = set()
        
        for chunk in chunks:
            try:
                # Get filename and source, with fallbacks
                filename = chunk.get('filename', 'Unknown Document')
                source = chunk.get('source', 'N/A')
                source_key = f"{filename} ({source})"
                
                # Only add unique sources
                if source_key not in seen_sources:
                    seen_sources.add(source_key)
                    sources.append({
                        'filename': filename,
                        'source': source,
                        'type': chunk.get('type', 'Unknown')
                    })
            except Exception as e:
                logger.error(f"Error processing chunk for sources: {str(e)}")
                continue
        
        # Format sources as strings for the frontend
        formatted_sources = []
        for src in sources:
            try:
                source_str = f"{src.get('filename', 'Unknown Document')}"
                if 'source' in src and src['source']:
                    source_str += f" (Page {src['source']})"
                if 'type' in src and src['type']:
                    source_str += f" - {src['type']}"
                formatted_sources.append(source_str)
            except Exception as e:
                logger.error(f"Error formatting source {src}: {str(e)}")
                formatted_sources.append("Unknown source")
        
        # Log the response and sources for debugging
        logger.debug(f"Generated response text: {response_text}")
        logger.debug(f"Formatted sources: {formatted_sources}")
        
        # Ensure sources are listed in the response
        if "SOURCES:" not in response_text.upper() and formatted_sources:
            sources_text = "\n".join([f"- {src}" for src in formatted_sources])
            response_text += f"\n\nSOURCES:\n{sources_text}"
        
        # Format the response
        response_data = {
            "response": response_text,
            "sources": formatted_sources,  # Now sending strings instead of objects
            "success": True
        }
        
        logger.debug(f"Returning response data: {json.dumps(response_data, indent=2)}")
        return response_data
        
    except Exception as e:
        error_msg = f"Error in generate_insights_from_chunks: {str(e)}"
        logger.error(error_msg)
        logger.exception("Stack trace:")
        
        # Include sources in error response if available
        sources = []
        if chunks:
            sources = list(set([
                f"{chunk['filename']} ({chunk['source']})" 
                for chunk in chunks
            ]))
            
        error_response = {
            "response": f"I encountered an error while generating a response: {str(e)}",
            "sources": sources,
            "success": False,
            "error": str(e)
        }
        logger.error(f"Error response: {json.dumps(error_response, indent=2)}")
        return error_response
