#!/usr/bin/env python3
"""
Test script for PDF processing pipeline
"""

import os
import sys
import requests
import json
from pathlib import Path

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent / 'backend'))

def test_pdf_upload():
    """Test PDF upload and processing"""
    
    # Test configuration
    server_url = "http://localhost:8000"
    test_pdf_path = "test.pdf"
    
    # Check if test PDF exists
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
    
    print(f"\n📄 Using test PDF: {test_pdf_path}")
    print(f"📏 File size: {os.path.getsize(test_pdf_path) / 1024:.2f} KB")
    
    # Test credentials
    username = "admin"
    password = "admin123"
    
    try:
        # Step 1: Login
        print(f"\n🔐 Logging in as {username}...")
        login_response = requests.post(
            f"{server_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return False
        
        token = login_response.json().get("access_token")
        if not token:
            print("❌ No access token received")
            return False
        
        print("✅ Login successful")
        
        # Step 2: Upload PDF
        print(f"\n📤 Uploading PDF...")
        
        with open(test_pdf_path, 'rb') as f:
            files = {
                'file': (os.path.basename(test_pdf_path), f, 'application/pdf')
            }
            data = {
                'description': 'Test PDF upload for pipeline verification',
                'rag_type': 'semantic'
            }
            
            upload_response = requests.post(
                f"{server_url}/api/upload/file",
                headers={"Authorization": f"Bearer {token}"},
                files=files,
                data=data
            )
        
        if upload_response.status_code != 200:
            print(f"❌ Upload failed: {upload_response.status_code}")
            print(f"Response: {upload_response.text}")
            return False
        
        upload_result = upload_response.json()
        print("✅ Upload successful")
        print(f"📋 Upload result: {json.dumps(upload_result, indent=2)}")
        
        # Step 3: Check file status
        if 'file_id' in upload_result:
            file_id = upload_result['file_id']
            print(f"\n📊 Checking file status for ID: {file_id}")
            
            status_response = requests.get(
                f"{server_url}/api/files/{file_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if status_response.status_code == 200:
                file_info = status_response.json()
                print(f"📈 File status: {file_info.get('status', 'unknown')}")
                print(f"📄 File info: {json.dumps(file_info, indent=2)}")
            else:
                print(f"⚠️ Could not get file status: {status_response.status_code}")
        
        # Step 4: List all files
        print(f"\n📋 Listing all files...")
        files_response = requests.get(
            f"{server_url}/api/files",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if files_response.status_code == 200:
            files_list = files_response.json()
            print(f"📁 Found {len(files_list)} files:")
            for file_info in files_list:
                print(f"  - {file_info.get('name', 'Unknown')} ({file_info.get('type', 'unknown')}) - {file_info.get('status', 'unknown')}")
        else:
            print(f"⚠️ Could not list files: {files_response.status_code}")
        
        print("\n✅ PDF pipeline test completed successfully!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing PDF Processing Pipeline")
    print("=" * 50)
    
    success = test_pdf_upload()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Tests failed!")
        sys.exit(1) 