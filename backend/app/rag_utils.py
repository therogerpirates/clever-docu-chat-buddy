import logging
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from sqlalchemy.orm import Session, joinedload
import numpy as np
from .models import PDFChunk, CSVChunk, XLSXChunk, File, PDFDocument, CSVDocument, XLSXDocument
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
        file_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search across all document chunks using stored embeddings.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            min_score: Minimum similarity score (0-1)
            file_type: Optional file type filter ('pdf', 'csv', 'xlsx')
            
        Returns:
            List of dictionaries containing chunk information and similarity scores
        """
        try:
            # Get query embedding
            query_embedding = await get_embedding(query)
            if not query_embedding:
                logger.error("Failed to get query embedding")
                return []
                
            results = []
            
            # Search in PDF chunks
            if file_type is None or file_type.lower() == 'pdf':
                pdf_chunks = self.db.query(PDFChunk).options(
                    joinedload(PDFChunk.document).joinedload(PDFDocument.file)
                ).all()
                
                for chunk in pdf_chunks:
                    try:
                        if not chunk.embedding:
                            continue
                            
                        # Convert JSON string to list if needed
                        chunk_embedding = chunk.embedding
                        if isinstance(chunk_embedding, str):
                            chunk_embedding = json.loads(chunk_embedding)
                            
                        # Calculate similarity
                        similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                        
                        if similarity >= min_score:
                            results.append({
                                'content': chunk.content,
                                'score': similarity,
                                'source': f"Page {chunk.page_number}",
                                'type': 'PDF',
                                'filename': chunk.document.file.original_filename,
                                'chunk_id': chunk.id,
                                'document_id': chunk.document_id
                            })
                    except Exception as e:
                        logger.error(f"Error processing PDF chunk {chunk.id}: {str(e)}")
                        continue
            
            # Search in CSV chunks (similar pattern as above)
            if file_type is None or file_type.lower() == 'csv':
                csv_chunks = self.db.query(CSVChunk).options(
                    joinedload(CSVChunk.document).joinedload(CSVDocument.file)
                ).all()
                
                for chunk in csv_chunks:
                    try:
                        if not chunk.embedding:
                            continue
                            
                        chunk_embedding = chunk.embedding
                        if isinstance(chunk_embedding, str):
                            chunk_embedding = json.loads(chunk_embedding)
                            
                        similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                        
                        if similarity >= min_score:
                            results.append({
                                'content': chunk.content,
                                'score': similarity,
                                'source': f"Row {chunk.row_number}",
                                'type': 'CSV',
                                'filename': chunk.document.file.original_filename,
                                'chunk_id': chunk.id,
                                'document_id': chunk.document_id
                            })
                    except Exception as e:
                        logger.error(f"Error processing CSV chunk {chunk.id}: {str(e)}")
                        continue
            
            # Search in XLSX chunks (similar pattern as above)
            if file_type is None or file_type.lower() == 'xlsx':
                xlsx_chunks = self.db.query(XLSXChunk).options(
                    joinedload(XLSXChunk.document).joinedload(XLSXDocument.file)
                ).all()
                
                for chunk in xlsx_chunks:
                    try:
                        if not chunk.embedding:
                            continue
                            
                        chunk_embedding = chunk.embedding
                        if isinstance(chunk_embedding, str):
                            chunk_embedding = json.loads(chunk_embedding)
                            
                        similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                        
                        if similarity >= min_score:
                            results.append({
                                'content': chunk.content,
                                'score': similarity,
                                'source': f"Sheet '{chunk.sheet_name}', Row {chunk.row_number}",
                                'type': 'XLSX',
                                'filename': chunk.document.file.original_filename,
                                'chunk_id': chunk.id,
                                'document_id': chunk.document_id
                            })
                    except Exception as e:
                        logger.error(f"Error processing XLSX chunk {chunk.id}: {str(e)}")
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
        chat = get_groq_chat(model_name=model_name)
        
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
        response_text = result.generations[0][0].text
        logger.info("Response generated successfully")
        
        # Extract and format sources from the chunks
        sources = []
        seen_sources = set()
        
        for chunk in chunks:
            source_key = f"{chunk['filename']} ({chunk['source']})"
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append(source_key)
        
        # Ensure sources are listed in the response
        if "SOURCES:" not in response_text.upper() and sources:
            response_text += "\n\nSOURCES:\n" + "\n".join(f"- {src}" for src in sources)
        
        return {
            "response": response_text,
            "sources": sources
        }
        
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
            
        return {
            "response": f"I encountered an error while generating a response: {str(e)}",
            "sources": sources
        }
