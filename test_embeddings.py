import os
import requests
import json
from dotenv import load_dotenv

def test_embeddings():
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment variables
    ollama_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    embedding_model = os.getenv("EMBEDDING_MODEL", "bge-m3:latest")
    
    print("Testing Embedding Service")
    print("=======================")
    print(f"Ollama API Base: {ollama_base}")
    print(f"Embedding Model: {embedding_model}")
    
    # Test text to generate embedding for
    test_text = "This is a test sentence to check if embeddings are working."
    
    print("\nSending request to Ollama API...")
    
    try:
        # Make the API request
        response = requests.post(
            f"{ollama_base}/api/embeddings",
            json={
                "model": embedding_model,
                "prompt": test_text
            },
            timeout=30  # 30 seconds timeout
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Get the response data
        data = response.json()
        
        # Print results
        print("\n✅ Success! Embedding generated successfully.")
        print(f"\nInput Text: {test_text}")
        print(f"\nEmbedding Vector (first 10 dimensions): {data['embedding'][:10]}...")
        print(f"Vector Length: {len(data['embedding'])}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print("\n❌ Error making request to Ollama API:")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            try:
                print(f"Response: {e.response.json()}")
            except:
                print(f"Response: {e.response.text}")
        else:
            print(str(e))
        
        return False
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    test_embeddings()
