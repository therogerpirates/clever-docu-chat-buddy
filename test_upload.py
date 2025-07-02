import requests
import os
import tempfile
from pathlib import Path

def test_file_upload():
    url = "http://localhost:8000/api/upload/test"
    temp_file = None
    
    try:
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp:
            test_content = b"This is a test file content for upload testing"
            temp.write(test_content)
            temp_file = temp.name
        
        # Prepare the file for upload using the file path directly
        with open(temp_file, 'rb') as f:
            files = {
                'file': (os.path.basename(temp_file), f, 'text/plain')
            }
            
            data = {
                'description': 'Test upload from script',
                'rag_type': 'semantic'
            }
            
            print(f"Uploading {temp_file} to {url}")
            response = requests.post(url, files=files, data=data)
            
            # Print the response
            print(f"Status Code: {response.status_code}")
            response_data = response.json()
            print("Response:", response_data)
            
            # Verify the file was saved
            if response.status_code == 200 and 'saved_as' in response_data:
                saved_path = Path(response_data['saved_as'])
                if saved_path.exists():
                    print(f"✅ File successfully saved to: {saved_path}")
                    print(f"File size: {saved_path.stat().st_size} bytes")
                    return True
                else:
                    print(f"❌ File not found at: {saved_path}")
                    return False
            return False
        # All processing is now done in the with block
        
    except Exception as e:
        print(f"Error during upload: {str(e)}")
        return False
    finally:
        # Clean up the temporary file if it exists
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception as e:
                print(f"Warning: Could not remove temp file: {e}")

if __name__ == "__main__":
    success = test_file_upload()
    if success:
        print("✅ Test upload successful!")
    else:
        print("❌ Test upload failed!")
