#!/usr/bin/env python3
"""
Test PDF processing utilities
"""

import os
import sys
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / 'app'))

def test_pdf_processing():
    """Test PDF processing utilities"""
    
    print("📄 Testing PDF Processing")
    print("=" * 40)
    
    try:
        # Test PDF file path
        test_pdf_path = "../test.pdf"
        
        if not os.path.exists(test_pdf_path):
            print(f"❌ Test PDF not found: {test_pdf_path}")
            print("Creating a test PDF...")
            
            # Create a simple test PDF
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                
                c = canvas.Canvas(test_pdf_path, pagesize=letter)
                width, height = letter
                
                c.setFont("Helvetica", 12)
                c.drawString(100, height - 100, "Test PDF Document")
                c.line(100, 95, 300, 95)
                
                c.setFont("Helvetica", 10)
                c.drawString(100, height - 150, "This is a test PDF document for verifying the upload functionality.")
                c.drawString(100, height - 170, "It contains sample text to test the PDF processing pipeline.")
                
                c.save()
                print(f"✅ Created test PDF: {test_pdf_path}")
            except ImportError:
                print("❌ reportlab not installed. Please install it with: pip install reportlab")
                return False
            except Exception as e:
                print(f"❌ Error creating test PDF: {e}")
                return False
        
        print(f"📄 Using test PDF: {test_pdf_path}")
        print(f"📏 File size: {os.path.getsize(test_pdf_path) / 1024:.2f} KB")
        
        # Test PDF utilities
        print("\n🔧 Testing PDF utilities...")
        from app.pdf_utils import extract_pdf_metadata, extract_pdf_content
        
        # Test metadata extraction
        print("📋 Testing metadata extraction...")
        metadata = extract_pdf_metadata(test_pdf_path)
        print(f"✅ Metadata extracted: {metadata}")
        
        # Test content extraction
        print("📝 Testing content extraction...")
        pages = extract_pdf_content(test_pdf_path)
        print(f"✅ Extracted {len(pages)} pages")
        
        for i, page in enumerate(pages[:2]):  # Show first 2 pages
            print(f"  Page {page['page_number']}: {len(page['content'])} characters")
            print(f"    Preview: {page['content'][:100]}...")
        
        # Test embedding generation (if Ollama is available)
        print("\n🧠 Testing embedding generation...")
        try:
            from app.pdf_utils import get_embedding_with_retry
            
            # Test with a small text sample
            test_text = "This is a test text for embedding generation."
            embedding = get_embedding_with_retry(test_text)
            print(f"✅ Embedding generated: {len(embedding)} dimensions")
            
        except Exception as e:
            print(f"⚠️ Embedding test failed (Ollama might not be running): {e}")
            print("   This is expected if Ollama is not running locally")
        
        print("\n✅ PDF processing test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ PDF processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pdf_processing()
    sys.exit(0 if success else 1) 