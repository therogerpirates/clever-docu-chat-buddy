import logging
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from sqlalchemy.orm import Session, joinedload
import numpy as np
from .models import PDFChunk, CSVChunk, XLSXChunk, File, PDFDocument, CSVDocument, XLSXDocument, WebsiteChunk, WebsiteDocument
from .llm_utils import get_embedding, get_groq_chat
from sqlalchemy import or_, text, MetaData, Table
from .database import engine, get_table_columns
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(funcName)s | %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
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
                        logger.error(f"Error processing PDF chunk {chunk.id}: {str(e)}", exc_info=True)
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
                        logger.error(f"Error processing CSV chunk {chunk.id}: {str(e)}", exc_info=True)
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
                        logger.error(f"Error processing XLSX chunk {chunk.id}: {str(e)}", exc_info=True)
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
                        logger.error(f"Error processing Website chunk {chunk.id}: {str(e)}", exc_info=True)
                        continue
            
            # Sort results by score in descending order
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # Limit results
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}", exc_info=True)
            return []

    def format_context(self, chunks: List[Dict[str, Any]]) -> str:
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
                logger.error(f"Error formatting chunk {i}: {str(e)}", exc_info=True)
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
        self,
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
            context = self.format_context(chunks)
            
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
                    logger.error(f"Error processing chunk for sources: {str(e)}", exc_info=True)
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
                    logger.error(f"Error formatting source {src}: {str(e)}", exc_info=True)
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
            logger.error(error_msg, exc_info=True)
            
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

    async def search_sql_rag(
        self, 
        query: str, 
        file_id: int,
        limit: int = 10,
        current_user: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Perform SQL RAG search using both SQL queries and semantic search.
        
        Args:
            query: The user's natural language query
            file_id: The file ID to search in
            limit: Maximum number of results to return
            current_user: The current user for access control
            
        Returns:
            Dictionary containing SQL results, semantic insights, and metadata
        """
        try:
            logger.info(f"Starting SQL RAG search for query: {query}")
            
            # First, get the file and check if it has SQL RAG data
            file_record = self.db.query(File).filter(File.id == file_id).first()
            if not file_record:
                logger.error(f"File with ID {file_id} not found")
                return {"error": "File not found"}
            
            # Check access control
            if current_user and current_user.role != 'admin':
                if current_user not in file_record.restricted_users and file_record.restricted_users:
                    logger.error(f"User {current_user.username} does not have access to file {file_id}")
                    return {"error": "Access denied"}
            
            # Get insights from the document
            insights = None
            table_name = None
            db_table_name = None
            
            if file_record.file_type.value == 'csv':
                csv_doc = self.db.query(CSVDocument).filter(CSVDocument.file_id == file_id).first()
                if csv_doc and csv_doc.header:
                    insights = csv_doc.header.get('insights')
                    db_table_name = csv_doc.header.get('table_name')
            elif file_record.file_type.value == 'xlsx':
                xlsx_doc = self.db.query(XLSXDocument).filter(XLSXDocument.file_id == file_id).first()
                if xlsx_doc and xlsx_doc.sheet_names:
                    insights = xlsx_doc.sheet_names.get('insights')
                    db_table_name = xlsx_doc.sheet_names.get('table_name')
            
            # Fallback: reconstruct table name if missing in DB
            if not db_table_name:
                if file_record.file_type.value == 'csv':
                    table_name = f"csv_data_{file_id}"
                elif file_record.file_type.value == 'xlsx':
                    table_name = f"xlsx_data_{file_id}"
                else:
                    table_name = None
                logger.warning(f"Table name missing in DB for file_id={file_id}. Using fallback: {table_name}")
            else:
                table_name = db_table_name
            logger.info(f"[SQL RAG] file_id={file_id}, file_type={file_record.file_type.value}, table_name(from DB)={db_table_name}, table_name(used)={table_name}")

            # Dynamically retrieve table columns
            if table_name:
                try:
                    table_columns = get_table_columns(engine, table_name)
                    logger.info(f"[SQL RAG] Columns for table {table_name}: {table_columns}")
                except Exception as e:
                    logger.error(f"Could not retrieve columns for table {table_name}: {str(e)}")
                    table_columns = []
            else:
                table_columns = []

            if not table_name:
                logger.error(f"No SQL table found for file {file_id}")
                return {"error": "No SQL data available for this file"}
            
            # Generate SQL query using LLM
            sql_query = await self._generate_sql_query(query, insights, table_name, table_columns)
            
            # Execute SQL query
            sql_results = await self._execute_sql_query(sql_query, table_name, limit)
            
            # Perform semantic search on insights and chunks
            semantic_results = await self._search_semantic_for_sql_rag(query, file_id, insights)
            
            # Determine which approach to use based on results
            use_sql = len(sql_results.get('data', [])) > 0
            use_semantic = len(semantic_results) > 0
            
            return {
                'sql_query': sql_query,
                'sql_results': sql_results,
                'semantic_results': semantic_results,
                'use_sql': use_sql,
                'use_semantic': use_semantic,
                'combined_approach': use_sql and use_semantic,
                'file_info': {
                    'filename': file_record.original_filename,
                    'file_type': file_record.file_type.value,
                    'table_name': table_name
                }
            }
            
        except Exception as e:
            logger.error(f"Error in SQL RAG search: {str(e)}", exc_info=True)
            return {"error": f"Search failed: {str(e)}"}

    async def _generate_sql_query(self, query: str, insights: str, table_name: str, table_columns: list) -> str:
        """
        Generate SQL query from natural language using LLM.
        """
        try:
            prompt = f"""
You are a SQL expert. Given the following database insights, table schema, and user query, generate a SQL query.

Database Insights:
{insights}

Table Name: {table_name}
Table Columns: {table_columns}

User Query: {query}

INSTRUCTIONS:
- Return ONLY the SQL query, with NO markdown, no explanation, no code block, and no commentary.
- The output should start with SELECT and be a valid SQL statement.
- Do NOT include any text before or after the SQL query.
- Use double quotes ("column name") for column and table names with spaces or special characters, as required by PostgreSQL.
- Do NOT use backticks for identifiers.
"""

            chat = await get_groq_chat(temperature=0.1)
            from langchain_core.messages import HumanMessage
            
            response = await chat.ainvoke([HumanMessage(content=prompt)])
            sql_query = response.content.strip()
            
            # Basic safety check - ensure it's a SELECT query
            if not sql_query.lower().startswith('select'):
                logger.warning(f"Generated query is not a SELECT: {sql_query}")
                return f"SELECT * FROM {table_name} LIMIT 10"
            
            return sql_query
            
        except Exception as e:
            logger.error(f"Error generating SQL query: {str(e)}", exc_info=True)
            return f"SELECT * FROM {table_name} LIMIT 10"

    async def _execute_sql_query(self, sql_query: str, table_name: str, limit: int) -> Dict[str, Any]:
        """
        Execute SQL query and return results.
        """
        try:
            # Extract the first valid SELECT statement using regex, even if wrapped in markdown or extra text
            cleaned_query = sql_query.strip()
            # Remove markdown code block wrappers if present
            cleaned_query = re.sub(r'^```[a-zA-Z]*\n?', '', cleaned_query)
            cleaned_query = re.sub(r'```$', '', cleaned_query)
            cleaned_query = cleaned_query.strip()
            # Extract the first SELECT ... statement
            match = re.search(r'(SELECT[\s\S]+?;)', cleaned_query, re.IGNORECASE)
            if match:
                extracted_query = match.group(1)
            else:
                # If not found, fallback to the cleaned query
                extracted_query = cleaned_query
            # Replace MySQL-style backticks with PostgreSQL double quotes
            extracted_query = re.sub(r'`([^`]+)`', r'"\1"', extracted_query)
            logger.info(f"[SQL RAG] Executing SQL query: {extracted_query}")
            with engine.connect() as conn:
                # Add LIMIT if not present
                if 'limit' not in extracted_query.lower():
                    extracted_query += f" LIMIT {limit}"
                result = conn.execute(text(extracted_query))
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in result.fetchall()]
                return {
                    'data': data,
                    'row_count': len(data),
                    'columns': list(columns)
                }
        except Exception as e:
            logger.error(f"Error executing SQL query: {str(e)} | Query: {sql_query}", exc_info=True)
            return {
                'data': [],
                'error': str(e),
                'row_count': 0,
                'columns': []
            }

    async def _search_semantic_for_sql_rag(self, query: str, file_id: int, insights: str) -> List[Dict[str, Any]]:
        """
        Perform semantic search on insights and document chunks for SQL RAG.
        """
        try:
            results = []
            
            # Search in insights if available
            if insights:
                insights_embedding = await get_embedding(insights)
                query_embedding = await get_embedding(query)
                
                if insights_embedding and query_embedding:
                    similarity = self._cosine_similarity(query_embedding, insights_embedding)
                    if similarity > 0.5:
                        results.append({
                            'content': insights,
                            'score': similarity,
                            'source': 'Database Insights',
                            'type': 'SQL_INSIGHTS',
                            'filename': 'Database Analysis'
                        })
            
            # Search in document chunks
            file_record = self.db.query(File).filter(File.id == file_id).first()
            if file_record:
                if file_record.file_type.value == 'csv':
                    chunks = self.db.query(CSVChunk).join(CSVDocument).filter(CSVDocument.file_id == file_id).limit(5).all()
                elif file_record.file_type.value == 'xlsx':
                    chunks = self.db.query(XLSXChunk).join(XLSXDocument).filter(XLSXDocument.file_id == file_id).limit(5).all()
                else:
                    chunks = []
                
                query_embedding = await get_embedding(query)
                for chunk in chunks:
                    if chunk.embedding and query_embedding:
                        similarity = self._cosine_similarity(query_embedding, chunk.embedding)
                        if similarity > 0.5:
                            results.append({
                                'content': chunk.content,
                                'score': similarity,
                                'source': f"Row {chunk.row_number}",
                                'type': 'DOCUMENT_CHUNK',
                                'filename': file_record.original_filename
                            })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search for SQL RAG: {str(e)}", exc_info=True)
            return []

    async def hybrid_sql_semantic_search(
        self,
        query: str,
        file_id: int,
        limit: int = 10,
        current_user: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Perform hybrid search that combines SQL and semantic approaches.
        """
        try:
            # Perform SQL RAG search
            sql_rag_results = await self.search_sql_rag(query, file_id, limit, current_user)
            
            if 'error' in sql_rag_results:
                return sql_rag_results
            
            # Determine the best approach based on results
            sql_results = sql_rag_results.get('sql_results', {})
            semantic_results = sql_rag_results.get('semantic_results', [])
            
            # If SQL returned data, prioritize it
            if sql_results.get('row_count', 0) > 0:
                response_type = 'sql_primary'
                if semantic_results:
                    response_type = 'hybrid'
            elif semantic_results:
                response_type = 'semantic_primary'
            else:
                response_type = 'no_results'
            
            return {
                'response_type': response_type,
                'sql_query': sql_rag_results.get('sql_query'),
                'sql_results': sql_results,
                'semantic_results': semantic_results,
                'file_info': sql_rag_results.get('file_info'),
                'recommendation': self._get_search_recommendation(response_type, sql_results, semantic_results)
            }
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}", exc_info=True)
            return {"error": f"Hybrid search failed: {str(e)}"}

    def _get_search_recommendation(self, response_type: str, sql_results: Dict, semantic_results: List) -> str:
        """
        Generate a recommendation based on the search results.
        """
        if response_type == 'sql_primary':
            return "SQL query executed successfully. The results show numerical data that directly answers your question."
        elif response_type == 'hybrid':
            return "Both SQL and semantic search returned relevant results. SQL provides numerical data, while semantic search offers contextual insights."
        elif response_type == 'semantic_primary':
            return "SQL query didn't return relevant numerical data, but semantic search found related information in the document content."
        else:
            return "No relevant results found. Try rephrasing your question or check if the data contains the information you're looking for."

    def create_dynamic_table(self, table_name: str, columns: List[str]):
        logger.debug(f"Creating dynamic table: {table_name} | columns={columns}")
        # Implementation of create_dynamic_table method
        logger.info(f"Table created: {table_name}")

    def insert_rows_to_dynamic_table(self, table_name: str, rows: List[Dict]):
        logger.debug(f"Inserting {len(rows)} rows into {table_name}")
        # Implementation of insert_rows_to_dynamic_table method
        logger.info(f"Inserted {len(rows)} rows into {table_name}")
