import requests
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API endpoint
API_URL = "http://localhost:8000/api/upload"

# Sample file path (replace with an actual file path for testing)
SAMPLE_FILE_PATH = "C:\\Users\\HARIHARAN\\OneDrive\\Documents\\Project report  FINAL.pdf"  # Test file provided by user
DESCRIPTION = "Test file upload"
RAG_TYPE = "semantic"

def test_upload_file(file_path=SAMPLE_FILE_PATH, description=DESCRIPTION, rag_type=RAG_TYPE):
    """
    Test file upload to the API endpoint.
    
    Args:
        file_path (str): Path to the file to upload.
        description (str): Description of the file.
        rag_type (str): Type of RAG to use.
    
    Returns:
        dict: Response from the API.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"status": "error", "message": f"File not found: {file_path}"}
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
            data = {
                'description': description,
                'rag_type': rag_type
            }
            response = requests.post(API_URL, files=files, data=data)
            response.raise_for_status()
            logger.info(f"File uploaded successfully: {file_path}")
            return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error uploading file: {str(e)}")
        logger.error(f"Response content: {e.response.text}")
        return {"status": "error", "message": str(e), "details": e.response.text}
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # You can replace SAMPLE_FILE_PATH with a real file path for testing
    result = test_upload_file()
    print(result)
