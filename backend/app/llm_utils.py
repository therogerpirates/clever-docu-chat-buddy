import os
import logging
import asyncio
import aiohttp
import sys
from datetime import datetime
from typing import List, Dict, Optional, Any, Type, TypeVar, Union, cast
from dotenv import load_dotenv

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables and verify required settings."""
    # Clear any existing environment variables to prevent conflicts
    if 'GROQ_API' in os.environ:
        del os.environ['GROQ_API']
    
    # Try to load from the project root .env file first
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    if os.path.exists(env_path):
        # Don't override existing variables to avoid loading from wrong .env file
        load_dotenv(env_path, override=False)
        logger.info(f"Loaded .env file from: {env_path}")
    
    # Verify required environment variables
    groq_api_key = os.getenv('GROQ_API')
    if not groq_api_key:
        # Try one more time with override in case the variable was in the system environment
        load_dotenv(env_path, override=True)
        groq_api_key = os.getenv('GROQ_API')
        if not groq_api_key:
            error_msg = "GROQ_API environment variable is not set. Please check your .env file."
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    # Clean up the API key (remove any quotes or whitespace)
    groq_api_key = groq_api_key.strip('"\'').strip()
    
    # Set the environment variable to ensure consistency
    os.environ['GROQ_API'] = groq_api_key
    
    logger.info("Environment variables loaded successfully")
    logger.info(f"Using model: {os.getenv('LLM_MODEL', 'meta-llama/llama-4-scout-17b-16e-instruct')}")
    logger.info(f"GROQ_API key loaded (first 5 and last 5 chars): {groq_api_key[:5]}...{groq_api_key[-5:] if groq_api_key else ''}")
    
    return groq_api_key

# Load environment on module import
try:
    GROQ_API_KEY = load_environment()
    logger.info("Groq API key loaded successfully")
except Exception as e:
    logger.error(f"Failed to load environment: {str(e)}")
    raise

# Check if langchain-groq is installed
try:
    import langchain_groq
    from langchain_groq import ChatGroq as LangChainChatGroq
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    HAS_GROQ = True
except ImportError:
    logger.warning("langchain-groq not installed. Install with: pip install langchain-groq")
    HAS_GROQ = False
    LangChainChatGroq = None
    HumanMessage = SystemMessage = AIMessage = None
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
        
        # Ensure API key is set
        groq_api_key = filtered_kwargs.get('groq_api_key') or os.getenv('GROQ_API')
        if not groq_api_key:
            raise ValueError("No GROQ API key provided and GROQ_API environment variable not set")
        
        # Always use the provided API key
        filtered_kwargs['groq_api_key'] = groq_api_key
        
        # Set default model if not provided
        if 'model_name' not in filtered_kwargs:
            filtered_kwargs['model_name'] = os.getenv('LLM_MODEL', 'meta-llama/llama-4-scout-17b-16e-instruct')
        
        logger.info(f"Initializing ChatGroq with model: {filtered_kwargs.get('model_name')}")
        logger.debug(f"API key: {groq_api_key[:5]}...{groq_api_key[-5:] if groq_api_key else ''}")
        
        try:
            # Initialize the parent class
            super().__init__(**filtered_kwargs)
            logger.info("Successfully initialized Groq client")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {str(e)}")
            raise

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Set log levels for specific loggers
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.DEBUG)

# Load environment variables
load_dotenv()

# Debug: Print all environment variables (without sensitive data)
logger.debug("Environment variables loaded")
logger.debug(f"GROQ_API present: {'GROQ_API' in os.environ}")
logger.debug(f"LLM_MODEL: {os.getenv('LLM_MODEL')}")

async def get_groq_chat(
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
) -> 'LangChainChatGroq':
    """Get a Groq chat model instance with the specified parameters.
    
    Args:
        model_name: The name of the model to use. If not provided, uses the default from environment.
        temperature: The temperature to use for generation.
        max_tokens: The maximum number of tokens to generate.
        **kwargs: Additional parameters to pass to the ChatGroq constructor.
        
    Returns:
        A configured ChatGroq instance.
        
    Raises:
        ImportError: If langchain-groq is not installed.
        ValueError: If required environment variables are missing.
        RuntimeError: If the Groq client cannot be initialized.
    """
    if not HAS_GROQ or not LangChainChatGroq:
        raise ImportError(
            "langchain-groq is not installed. Please install it with: pip install langchain-groq"
        )
    
    # Use the preloaded API key from module level
    groq_api_key = globals().get('GROQ_API_KEY')
    if not groq_api_key:
        raise ValueError("Failed to load GROQ_API_KEY. Check your .env file and restart the server.")
    
    # Get the model name from environment if not provided
    model_name = model_name or os.getenv('LLM_MODEL', 'meta-llama/llama-4-scout-17b-16e-instruct')
    logger.info(f"Initializing Groq chat with model: {model_name}")
    
    try:
        # Create the chat model
        chat = LangChainChatGroq(
            api_key=groq_api_key,  # Explicitly pass the API key
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens or 2048,  # Default to 2048 if not specified
            streaming=False,  # Disable streaming for now
            verbose=True,
            **kwargs
        )
        
        # Test the connection with a simple message (async)
        logger.info("Testing Groq API connection...")
        try:
            test_messages = [HumanMessage(content="Hello, this is a test.")]
            # Use ainvoke for async invocation
            response = await chat.ainvoke(test_messages)
            logger.info(f"Successfully connected to Groq API. Response: {response}")
            return chat
            
        except Exception as test_error:
            error_msg = f"Failed to connect to Groq API: {str(test_error)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from test_error
            
    except Exception as e:
        error_msg = f"Failed to initialize Groq chat: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e

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
        Dict containing the AI response and metadata with the following structure:
        {
            'success': bool,           # Whether the request was successful
            'response': str,          # The generated response content
            'model': str,             # The model used
            'timestamp': str,         # ISO format timestamp
            'duration_seconds': float # Time taken in seconds
        }
        
    Raises:
        ValueError: If there's an error in the request or response processing
        RuntimeError: If there's an error communicating with the Groq API
    """
    start_time = datetime.utcnow()
    
    try:
        # Set up model name and log start
        model_name = model_name or os.getenv('LLM_MODEL', 'meta-llama/llama-4-scout-17b-16e-instruct')
        logger.info(f"Starting chat generation with model: {model_name}")
        
        # Initialize the chat model
        logger.info(f"Initializing ChatGroq with model: {model_name}")
        try:
            chat = await get_groq_chat(model_name=model_name, **kwargs)
            logger.info("Successfully initialized chat model")
        except Exception as e:
            error_msg = f"Failed to initialize chat model: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
        
        # Prepare messages for the model
        lc_messages = []
        
        # Add system prompt if provided
        if system_prompt:
            logger.debug(f"Adding system prompt: {system_prompt[:100]}...")
            lc_messages.append(SystemMessage(content=system_prompt))
        
        # Process each message
        for msg in messages:
            if not isinstance(msg, dict):
                logger.warning(f"Skipping invalid message (not a dict): {msg}")
                continue
                
            role = str(msg.get('role', '')).lower()
            content = str(msg.get('content', ''))
            
            if not content.strip():
                logger.warning(f"Skipping empty message with role: {role}")
                continue
            
            try:
                if role == 'user':
                    lc_messages.append(HumanMessage(content=content))
                elif role == 'assistant':
                    lc_messages.append(AIMessage(content=content))
                elif role == 'system':
                    lc_messages.append(SystemMessage(content=content))
                else:
                    logger.warning(f"Unknown message role: {role}, treating as user message")
                    lc_messages.append(HumanMessage(content=content))
                
                logger.debug(f"Added message (role: {role}): {content[:100]}...")
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                continue
        
        # Validate we have messages to send
        if not lc_messages:
            error_msg = "No valid messages to send to the model"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Sending {len(lc_messages)} messages to Groq")
        
        try:
            # Generate the response
            logger.debug("Invoking chat model...")
            start_invoke = datetime.utcnow()
            response = await chat.ainvoke(lc_messages)
            invoke_duration = (datetime.utcnow() - start_invoke).total_seconds()
            
            # Process the response
            if hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, str):
                content = response
            elif hasattr(response, 'text'):
                content = response.text
            else:
                content = str(response)
                logger.warning(f"Unexpected response format: {type(response)}")
            
            # Calculate total duration
            total_duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log success
            logger.info(f"Chat response generated in {total_duration:.2f}s (API: {invoke_duration:.2f}s)")
            logger.debug(f"Response content: {content[:200]}..." if len(str(content)) > 200 else f"Response: {content}")
            
            # Return successful response
            return {
                'success': True,
                'response': content,
                'model': model_name,
                'timestamp': datetime.utcnow().isoformat(),
                'duration_seconds': total_duration,
                'api_duration_seconds': invoke_duration
            }
            
        except Exception as e:
            error_msg = f"Error invoking Groq API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
            
    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        error_msg = f"Error generating chat response after {duration:.2f}s: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Return a structured error response
        return {
            'success': False,
            'error': str(e),
            'model': model_name or 'unknown',
            'timestamp': datetime.utcnow().isoformat(),
            'duration_seconds': duration
        }

async def get_embedding_with_retry(text: str, max_retries: int = 3, initial_delay: float = 1.0) -> Optional[List[float]]:
    """
    Get embeddings for text with retry logic.
    
    Args:
        text: Text to get embeddings for
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        
    Returns:
        List of floats representing the embedding, or None if all retries fail
    """
    last_exception = None
    delay = initial_delay
    model = os.getenv("EMBEDDING_MODEL", "bge-m3:latest")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries} to get embedding using model: {model}")
            embedding = await get_embedding(text)
            
            if not embedding or len(embedding) == 0:
                raise ValueError("Received empty embedding")
                
            logger.info(f"Successfully generated embedding with {len(embedding)} dimensions")
            return embedding
            
        except asyncio.TimeoutError as e:
            last_exception = e
            logger.warning(f"Timeout error on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                logger.error("Max retries reached for timeout error")
                raise
                
        except aiohttp.ClientError as e:
            last_exception = e
            logger.error(f"HTTP client error on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                logger.error("Max retries reached for HTTP client error")
                raise
                
        except ValueError as e:
            last_exception = e
            logger.error(f"Value error on attempt {attempt + 1}: {str(e)}")
            if "empty" in str(e).lower() or "invalid" in str(e).lower():
                logger.error("Not retrying due to data validation error")
                break
                
        except Exception as e:
            last_exception = e
            logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}", exc_info=True)
            
        if attempt < max_retries - 1:
            logger.warning(f"Retrying in {delay:.1f} seconds... (attempt {attempt + 2}/{max_retries})")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)  # Exponential backoff with max 30 seconds
    
    error_msg = f"Failed to get embedding after {max_retries} attempts. Last error: {str(last_exception)}"
    logger.error(error_msg)
    logger.error(f"Model: {model}")
    logger.error(f"Text length: {len(text)} characters")
    logger.error(f"Text preview: {text[:100]}...")
    
    return None


async def get_embedding(text: str, model: Optional[str] = None) -> List[float]:
    """
    Get embeddings for text using Ollama's API.
    
    Args:
        text: Text to get embeddings for
        model: Optional model name to use for embeddings (defaults to EMBEDDING_MODEL from env)
        
    Returns:
        List of floats representing the embedding
    
    Raises:
        Exception: If there's an error getting the embedding
    """
    try:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Get model and base URL from environment with fallbacks
        model = model or os.getenv("EMBEDDING_MODEL", "bge-m3:latest")
        ollama_base_url = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        
        logger.info(f"Getting embedding for text (first 50 chars): {text[:50]}...")
        logger.info(f"Using model: {model}")
        logger.info(f"Ollama base URL: {ollama_base_url}")
        
        # Validate URL
        if not ollama_base_url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid Ollama base URL: {ollama_base_url}")
        
        # Prepare request URL
        url = f"{ollama_base_url.rstrip('/')}/api/embeddings"
        logger.info(f"Sending request to: {url}")
        
        # Prepare request data
        data = {"model": model, "prompt": text}
        
        # Call Ollama's embedding API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=data,
                    timeout=60
                ) as response:
                    logger.info(f"Received response status: {response.status}")
                    
                    response_text = await response.text()
                    logger.debug(f"Raw response: {response_text}")
                    
                    if response.status != 200:
                        logger.error(f"Error from Ollama API (HTTP {response.status}): {response_text}")
                        raise Exception(f"Ollama API error: {response.status} - {response_text}")
                    
                    try:
                        result = await response.json()
                    except Exception as e:
                        logger.error(f"Failed to parse JSON response: {e}\nResponse: {response_text}")
                        raise ValueError(f"Invalid JSON response: {response_text}")
                    
                    if 'embedding' not in result:
                        error_msg = f"Unexpected response format from Ollama. Missing 'embedding' key. Response: {result}"
                        logger.error(error_msg)
                        raise ValueError("Invalid response format from embedding service: missing 'embedding' key")
                    
                    embedding = result['embedding']
                    
                    # Check if embedding is empty or invalid
                    if not embedding:
                        error_msg = "Received empty embedding from Ollama API"
                        logger.error(error_msg)
                        raise ValueError(error_msg)
                        
                    if not isinstance(embedding, list):
                        error_msg = f"Embedding is not a list: {type(embedding)}"
                        logger.error(error_msg)
                        raise ValueError(error_msg)
                        
                    if not all(isinstance(x, (int, float)) for x in embedding):
                        error_msg = f"Embedding contains non-numeric values. First 5 items: {embedding[:5]}"
                        logger.error(error_msg)
                        raise ValueError("Invalid embedding format: expected list of numbers")
                    
                    embedding_length = len(embedding)
                    if embedding_length == 0:
                        error_msg = "Received zero-dimensional embedding"
                        logger.error(error_msg)
                        raise ValueError(error_msg)
                        
                    logger.info(f"Successfully got embedding with {embedding_length} dimensions")
                    logger.debug(f"First 5 embedding values: {embedding[:5]}")
                    return embedding
                    
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout while getting embeddings from Ollama after 60 seconds: {str(e)}")
            raise
            
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error while connecting to Ollama at {url}: {str(e)}")
            logger.error("Please verify that:")
            logger.error(f"1. Ollama is running at {ollama_base_url}")
            logger.error(f"2. The model '{model}' is available (run 'ollama list' to check)")
            logger.error(f"3. The Ollama service is accessible from this machine")
            logger.error(f"4. No firewall is blocking the connection to {ollama_base_url}")
            raise
            
    except Exception as e:
        logger.error(f"Unexpected error in get_embedding: {str(e)}", exc_info=True)
        raise