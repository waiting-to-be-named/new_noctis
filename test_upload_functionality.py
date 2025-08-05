#!/usr/bin/env python3
"""
Test script to verify DICOM upload functionality
"""

import requests
import os
import tempfile
import time

def test_upload_endpoint():
    """Test the upload endpoint to see if it's working"""
    
    # Test the upload endpoint
    url = "http://localhost:8000/viewer/api/upload-dicom-files/"
    
    # Create a simple test file (not a real DICOM, but enough to test the endpoint)
    with tempfile.NamedTemporaryFile(suffix='.dcm', delete=False) as f:
        f.write(b'DICM\x00\x00\x00\x00')  # Minimal DICOM header
        test_file_path = f.name
    
    try:
        # Test if server is running
        print("Testing server connectivity...")
        try:
            response = requests.get("http://localhost:8000/", timeout=5)
            print(f"✅ Server is running (status: {response.status_code})")
        except requests.exceptions.ConnectionError:
            print("❌ Server is not running. Please start the Django server first.")
            return False
        
        # Test upload endpoint
        print("\nTesting upload endpoint...")
        with open(test_file_path, 'rb') as f:
            files = {'files': ('test.dcm', f, 'application/dicom')}
            response = requests.post(url, files=files, timeout=30)
        
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Upload endpoint is working!")
            return True
        else:
            print("❌ Upload endpoint returned an error")
            return False
            
    except Exception as e:
        print(f"❌ Error testing upload: {e}")
        return False
    finally:
        # Clean up test file
        if os.path.exists(test_file_path):
            os.unlink(test_file_path)

def test_worklist_upload():
    """Test the worklist upload functionality"""
    
    print("\nTesting worklist upload functionality...")
    
    # Check if worklist template has real upload implementation
    worklist_template_path = "templates/worklist/worklist.html"
    
    if os.path.exists(worklist_template_path):
        with open(worklist_template_path, 'r') as f:
            content = f.read()
            
        if 'FormData' in content and 'fetch' in content:
            print("✅ Worklist template has real upload implementation")
        else:
            print("❌ Worklist template has fake upload (simulation only)")
            print("   The upload in worklist is just a simulation, not real upload")
            return False
    else:
        print("❌ Worklist template not found")
        return False
    
    return True

def main():
    """Main test function"""
    print("🔍 Testing DICOM Upload Functionality")
    print("=" * 50)
    
    # Test 1: Check if server is running and upload endpoint works
    upload_works = test_upload_endpoint()
    
    # Test 2: Check worklist upload implementation
    worklist_upload_works = test_worklist_upload()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"Server & Upload Endpoint: {'✅ Working' if upload_works else '❌ Failed'}")
    print(f"Worklist Upload: {'✅ Real Implementation' if worklist_upload_works else '❌ Fake Implementation'}")
    
    if upload_works and worklist_upload_works:
        print("\n🎉 All upload functionality is working correctly!")
    elif upload_works and not worklist_upload_works:
        print("\n⚠️  Server upload works, but worklist has fake upload")
        print("   Recommendation: Use the advanced viewer for real uploads")
    else:
        print("\n❌ Upload functionality has issues")
        print("   Recommendation: Check server logs and fix upload implementation")

if __name__ == "__main__":
    main()