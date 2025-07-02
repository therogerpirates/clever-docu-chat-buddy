#!/usr/bin/env python3
"""
Comprehensive fix for PDF upload pipeline
"""

import os
import sys
import shutil
from pathlib import Path

def fix_environment():
    """Fix environment variables"""
    print("🔧 Fixing environment variables...")
    
    # Get the current script directory
    script_dir = Path(__file__).parent
    print(f"📁 Script directory: {script_dir}")
    
    # Copy env file to backend/.env
    env_source = script_dir / "env"
    env_dest = script_dir / "backend" / ".env"
    
    # Ensure the backend directory exists
    env_dest.parent.mkdir(parents=True, exist_ok=True)
    
    if env_source.exists():
        shutil.copy2(env_source, env_dest)
        print(f"✅ Copied environment variables from {env_source} to {env_dest}")
    else:
        print("⚠️ env file not found, creating basic .env file...")
        
        # Create basic .env file
        env_content = """DATABASE_URL=postgresql://linkedin_owner:npg_aJcpCgkA1RN6@ep-quiet-tree-a5o8mr54-pooler.us-east-2.aws.neon.tech/linkedin?sslmode=require
GROQ_API=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
OLLAMA_API_BASE=http://localhost:11434
EMBEDDING_MODEL=bge-m3:latest
LLM_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
EMBEDDING_RETRY_DELAY=5
EMBEDDING_MAX_RETRIES=3
JWT_SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
"""
        
        with open(env_dest, 'w') as f:
            f.write(env_content)
        print(f"✅ Created basic .env file at {env_dest}")

def install_dependencies():
    """Install missing dependencies"""
    print("\n📦 Installing dependencies...")
    
    script_dir = Path(__file__).parent
    backend_dir = script_dir / "backend"
    requirements_file = backend_dir / "requirements.txt"
    
    if requirements_file.exists():
        print(f"📋 Installing requirements from {requirements_file}...")
        os.system(f"cd {backend_dir} && pip install -r requirements.txt")
        print("✅ Dependencies installed")
    else:
        print(f"❌ requirements.txt not found at {requirements_file}")

def create_test_pdf():
    """Create a test PDF if it doesn't exist"""
    print("\n📄 Creating test PDF...")
    
    script_dir = Path(__file__).parent
    test_pdf_path = script_dir / "test.pdf"
    
    if not test_pdf_path.exists():
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            c = canvas.Canvas(str(test_pdf_path), pagesize=letter)
            width, height = letter
            
            c.setFont("Helvetica", 12)
            c.drawString(100, height - 100, "Test PDF Document")
            c.line(100, 95, 300, 95)
            
            c.setFont("Helvetica", 10)
            c.drawString(100, height - 150, "This is a test PDF document for verifying the upload functionality.")
            c.drawString(100, height - 170, "It contains sample text to test the PDF processing pipeline.")
            c.drawString(100, height - 190, "This document will be used to test the PDF upload and processing pipeline.")
            c.drawString(100, height - 210, "The system should be able to extract text, generate embeddings, and store them in the database.")
            
            c.save()
            print(f"✅ Created test PDF: {test_pdf_path}")
        except ImportError:
            print("❌ reportlab not installed. Please install it with: pip install reportlab")
        except Exception as e:
            print(f"❌ Error creating test PDF: {e}")
    else:
        print(f"✅ Test PDF already exists: {test_pdf_path}")

def run_tests():
    """Run the test scripts"""
    print("\n🧪 Running tests...")
    
    script_dir = Path(__file__).parent
    backend_dir = script_dir / "backend"
    
    # Test database connection
    print("\n🔍 Testing database connection...")
    os.system(f"cd {backend_dir} && python test_database.py")
    
    # Test PDF processing
    print("\n📄 Testing PDF processing...")
    os.system(f"cd {backend_dir} && python test_pdf_processing.py")
    
    # Test full pipeline
    print("\n🚀 Testing full pipeline...")
    os.system(f"cd {script_dir} && python test_pdf_pipeline.py")

def main():
    """Main fix function"""
    print("🔧 PDF Upload Pipeline Fix")
    print("=" * 50)
    
    # Fix environment
    fix_environment()
    
    # Install dependencies
    install_dependencies()
    
    # Create test PDF
    create_test_pdf()
    
    # Run tests
    run_tests()
    
    print("\n🎉 PDF pipeline fix completed!")
    print("\n📋 Next steps:")
    print("1. Start the backend server: cd clever-docu-chat-buddy/backend && python -m uvicorn app.main:app --reload")
    print("2. Start the frontend: cd clever-docu-chat-buddy && npm run dev")
    print("3. Test the upload functionality in the web interface")

if __name__ == "__main__":
    main() 