import os
import logging
import asyncio
import aiohttp
from typing import List, Dict, Optional, Any, Type, TypeVar, Union, cast
from dotenv import load_dotenv

# Import from langchain
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)

# Import Groq from langchain_groq
try:
    from langchain_groq import ChatGroq as LangChainGroq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    LangChainGroq = None

logger = logging.getLogger(__name__)

class ChatGroq(LangChainGroq):
    """Wrapper around LangChain's ChatGroq to handle version 0.3.2 specific behavior."""
    
    def __init__(self, **kwargs):
        # Filter out any None values to avoid passing them to the parent class
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        # Ensure required parameters are set
        if 'groq_api_key' not in filtered_kwargs:
            filtered_kwargs['groq_api_key'] = os.getenv('GROQ_API')
            
        if not filtered_kwargs.get('groq_api_key'):
            raise ValueError("GROQ_API environment variable not set or no API key provided")
            
        # Set default model if not provided
        if 'model_name' not in filtered_kwargs:
            filtered_kwargs['model_name'] = os.getenv('LLM_MODEL', 'meta-llama/llama-4-scout-17b-16e-instruct')
            
        logger.info(f"Initializing ChatGroq with model: {filtered_kwargs.get('model_name')}")
        
        # Initialize the parent class
        super().__init__(**filtered_kwargs)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_groq_chat(model_name: Optional[str] = None) -> ChatGroq:
    """
    Initialize and return a Groq chat model using langchain-groq 0.3.2.
    
    Args:
        model_name: Optional model name to override the default from environment
        
    Returns:
        Initialized ChatGroq instance
    """
    try:
        if not HAS_GROQ:
            raise ImportError("langchain-groq package is not installed. Please install it with: pip install langchain-groq==0.3.2")
        
        logger.info(f"Initializing ChatGroq with model: {model_name}")
        
        # Initialize with only the parameters we want to use
        chat = ChatGroq(
            model_name=model_name,
            temperature=0.7,  # Adjust temperature as needed
            max_tokens=2048,  # Adjust max tokens as needed
            streaming=False,   # Disable streaming for now
            verbose=True
        )
        
        logger.info("Successfully initialized ChatGroq")
        return chat
        
    except Exception as e:
        error_msg = f"Error initializing ChatGroq: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full traceback:")
        raise ValueError(error_msg) from e

async def generate_chat_response(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Generate a chat response using Groq via langchain-groq 0.3.2.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        system_prompt: Optional system prompt to guide the model
        model_name: Optional model name to override the default
        **kwargs: Additional arguments that will be passed to the model
        
    Returns:
        Dict containing the AI response and metadata
    """
    try:
        logger.info(f"Starting chat generation with model: {model_name}")
        
        # Initialize chat model
        try:
            chat = get_groq_chat(model_name=model_name)
            logger.info("Successfully initialized chat model")
        except Exception as e:
            error_msg = f"Failed to initialize chat model: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "response": "Failed to initialize the chat model. Please check the logs."}
        
        # Convert messages to LangChain format
        lc_messages = []
        
        # Add system prompt if provided
        if system_prompt:
            logger.debug(f"Adding system prompt: {system_prompt}")
            lc_messages.append(SystemMessage(content=system_prompt))
        
        # Convert messages to LangChain format
        for i, msg in enumerate(messages):
            role = msg.get("role", "").lower()
            content = str(msg.get("content", ""))
            
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system" and not system_prompt:  # Only add if not already added
                lc_messages.append(SystemMessage(content=content))
            
            # Log first 50 chars of each message for debugging
            logger.debug(f"Added message {i+1} (role: {role}): {content[:50]}...")
        
        logger.info(f"Sending {len(lc_messages)} messages to Groq")
        
        try:
            # Generate response using ainvoke for async compatibility
            logger.debug("Calling chat.ainvoke()")
            response = await chat.ainvoke(lc_messages)
            
            if not response or not hasattr(response, 'content'):
                error_msg = "Invalid response format from Groq"
                logger.error(error_msg)
                return {"error": error_msg, "response": "Received an invalid response from the AI service."}
            
            # Extract the generated message
            ai_message = response.content if hasattr(response, 'content') else str(response)
            logger.info("Successfully received response from Groq")
            
            # Prepare the response
            response_data = {
                "response": ai_message,
                "model": model_name or os.getenv("LLM_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"),
                "usage": {}
            }
            
            # Try to get usage metadata if available
            try:
                if hasattr(response, 'response_metadata') and hasattr(response.response_metadata, 'token_usage'):
                    token_usage = response.response_metadata.token_usage
                    response_data["usage"] = {
                        "prompt_tokens": getattr(token_usage, 'prompt_tokens', None),
                        "completion_tokens": getattr(token_usage, 'completion_tokens', None),
                        "total_tokens": getattr(token_usage, 'total_tokens', None)
                    }
                elif hasattr(response, 'usage'):
                    # Fallback to direct usage attribute if available
                    response_data["usage"] = {
                        "prompt_tokens": getattr(response.usage, 'prompt_tokens', None),
                        "completion_tokens": getattr(response.usage, 'completion_tokens', None),
                        "total_tokens": getattr(response.usage, 'total_tokens', None)
                    }
            except Exception as e:
                logger.warning(f"Could not extract usage metadata: {str(e)}")
            
            return response_data
            
        except Exception as e:
            error_msg = f"Error during chat generation: {str(e)}"
            logger.error(error_msg)
            logger.exception("Full traceback:")
            return {"error": error_msg, "response": "An error occurred while generating the response."}
        
    except Exception as e:
        error_msg = f"Unexpected error in generate_chat_response: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full traceback:")
        return {"error": error_msg, "response": "An unexpected error occurred. Please try again."}

async def get_embedding(text: str, model: Optional[str] = None) -> List[float]:
    """
    Get embeddings for text using Ollama's API.
    
    Args:
        text: Text to get embeddings for
        model: Optional model name to use for embeddings (defaults to EMBEDDING_MODEL from env)
        
    Returns:
        List of floats representing the embedding
    """
    try:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
            
        model = model or os.getenv("EMBEDDING_MODEL", "bge-m3:latest")
        ollama_base_url = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        
        # Call Ollama's embedding API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ollama_base_url.strip('/')}/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=60
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error from Ollama API: {error_text}")
                    raise Exception(f"Ollama API error: {response.status} - {error_text}")
                
                result = await response.json()
                
                if 'embedding' not in result:
                    logger.error(f"Unexpected response format from Ollama: {result}")
                    raise ValueError("Invalid response format from embedding service")
                
                return result['embedding']
                
    except asyncio.TimeoutError:
        logger.error("Timeout while getting embeddings from Ollama")
        raise
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error while getting embeddings: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise