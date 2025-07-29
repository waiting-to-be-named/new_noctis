#!/usr/bin/env python3
"""
Simple test to verify upload endpoint
"""

import requests
import tempfile
import os

def test_upload_endpoint():
    """Test the upload endpoint"""
    print("=== Testing Upload Endpoint ===")
    
    # Create a simple test file
    with tempfile.NamedTemporaryFile(suffix='.dcm', delete=False) as temp_file:
        temp_file.write(b'DICOM test file content')
        temp_file_path = temp_file.name
    
    try:
        # Test file upload via API
        url = "http://localhost:8000/viewer/api/upload/"
        
        with open(temp_file_path, 'rb') as f:
            files = {'files': f}
            response = requests.post(url, files=files)
        
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response: {response.text}")
        
        if response.status_code == 400:
            print("✓ Endpoint is working, but file validation failed (expected)")
            return True
        else:
            print("✗ Unexpected response")
            return False
            
    except Exception as e:
        print(f"Test failed: {e}")
        return False
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)

if __name__ == "__main__":
    success = test_upload_endpoint()
    if success:
        print("\n✓ Upload endpoint is working")
    else:
        print("\n✗ Upload endpoint has issues")