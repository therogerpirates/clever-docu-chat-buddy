import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add the current directory to the Python path
sys.path.append(str(Path(__file__).parent))

# Load environment variables
env_path = Path('.env')
if not env_path.exists():
    raise FileNotFoundError(f"Environment file not found at: {env_path}")
load_dotenv(env_path)

from app.database import SessionLocal
from app.rag_utils import VectorStore, generate_insights_from_chunks

async def test_rag():
    """Test the RAG pipeline with a sample query."""
    db = SessionLocal()
    try:
        print("\n=== Testing RAG Pipeline ===")
        
        # Test query
        test_query = "What is this document about?"
        print(f"\nTest query: {test_query}")
        
        # Step 1: Test semantic search
        print("\n--- Testing Semantic Search ---")
        vector_store = VectorStore(db)
        chunks = await vector_store.search_semantic(
            query=test_query,
            limit=3,
            min_score=0.3  # Lower threshold for testing
        )
        
        if not chunks:
            print("No chunks found. Possible issues:")
            print("1. The embeddings might not be properly stored")
            print("2. The similarity threshold might be too high")
            print("3. The query might be too different from the document content")
            return
            
        print(f"Found {len(chunks)} relevant chunks:")
        for i, chunk in enumerate(chunks, 1):
            print(f"\n--- Chunk {i} (Score: {chunk['score']:.3f}) ---")
            print(f"Source: {chunk.get('source', 'N/A')}")
            print(f"Type: {chunk.get('type', 'N/A')}")
            print(f"Content: {chunk['content'][:200]}...")
        
        # Step 2: Test insights generation
        print("\n--- Testing Insights Generation ---")
        insights = await generate_insights_from_chunks(
            query=test_query,
            chunks=chunks,
            model_name=os.getenv("LLM_MODEL")
        )
        
        print("\n=== RAG Response ===")
        print(insights.get('response', 'No response generated'))
        print("\nSources:", insights.get('sources', []))
        
    except Exception as e:
        print(f"\nError in RAG pipeline: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_rag())
