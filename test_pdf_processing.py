import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv
import json

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent / 'backend'))

# Load environment variables
load_dotenv()

def test_pdf_processing():
    print("Testing PDF Processing Pipeline")
    print("============================")
    
    # Test PDF file (you can replace this with your own test PDF)
    test_pdf_path = "test.pdf"
    
    if not os.path.exists(test_pdf_path):
        print(f"\n❌ Test PDF file not found at: {test_pdf_path}")
        print("Please create a test PDF file or update the path in the script.")
        return False
    
    print(f"\nUsing test PDF: {test_pdf_path}")
    print(f"File size: {os.path.getsize(test_pdf_path) / 1024:.2f} KB")
    
    # Get the FastAPI server URL
    server_url = "http://localhost:8000"  # Update if your server runs on a different port
    
    # Get test credentials from environment variables
    username = os.getenv("TEST_USERNAME", "admin")
    password = os.getenv("TEST_PASSWORD", "admin123")
    
    print(f"\nAuthenticating as user: {username}")
    
    try:
        # Step 1: Login to get auth token
        login_url = f"{server_url}/api/auth/login"
        login_data = {
            "username": username,
            "password": password
        }
        
        print(f"Login request data: {login_data}")
        print(f"Login URL: {login_url}")
        
        print(f"\n1. Logging in to {login_url}...")
        response = requests.post(login_url, json=login_data)
        response.raise_for_status()
        
        token = response.json().get("access_token")
        if not token:
            print("❌ Failed to get access token")
            return False
            
        print("✅ Login successful")
        
        # Step 2: Upload the PDF file
        upload_url = f"{server_url}/api/upload/file"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        print(f"\n2. Uploading PDF file to {upload_url}...")
        
        with open(test_pdf_path, 'rb') as f:
            files = {
                'file': (os.path.basename(test_pdf_path), f, 'application/pdf')
            }
            data = {
                'description': 'Test PDF upload',
                'rag_type': 'semantic'
            }
            
            response = requests.post(
                upload_url,
                headers=headers,
                files=files,
                data=data
            )
        
        response.raise_for_status()
        upload_result = response.json()
        
        print("✅ File uploaded successfully")
        print(f"Upload Result: {json.dumps(upload_result, indent=2)}")
        
        # Step 3: Check file status
        if 'file_id' in upload_result:
            file_id = upload_result['file_id']
            status_url = f"{server_url}/api/files/{file_id}"
            
            print(f"\n3. Checking file processing status at {status_url}...")
            
            # Wait for processing to complete (polling)
            max_attempts = 10
            for attempt in range(max_attempts):
                response = requests.get(status_url, headers=headers)
                response.raise_for_status()
                
                file_status = response.json()
                status = file_status.get('status', '').lower()
                
                print(f"  Attempt {attempt + 1}/{max_attempts}: Status = {status}")
                
                if status == 'ready':
                    print("\n✅ PDF processing completed successfully!")
                    print(f"File ID: {file_id}")
                    return True
                elif status == 'error':
                    print(f"\n❌ Error processing PDF: {file_status.get('error_message', 'Unknown error')}")
                    return False
                
                # Wait before next attempt
                import time
                time.sleep(2)
            
            print(f"\n❌ Processing timed out after {max_attempts} attempts")
            return False
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            try:
                print(f"Response: {json.dumps(e.response.json(), indent=2)}")
            except:
                print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_pdf_processing()
