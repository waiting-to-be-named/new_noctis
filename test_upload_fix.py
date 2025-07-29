#!/usr/bin/env python3
"""
Test script to verify DICOM upload functionality is working
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
import tempfile
import pydicom
from pydicom.dataset import Dataset
import io

class DicomUploadTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create a test client
        self.client = Client()
        
        # Login the user
        self.client.login(username='testuser', password='testpass123')
    
    def create_test_dicom_file(self):
        """Create a simple test DICOM file"""
        # Create a minimal DICOM dataset
        ds = Dataset()
        ds.PatientName = "Test^Patient"
        ds.PatientID = "12345"
        ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9"
        ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.9.1"
        ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.9.1.1"
        ds.Modality = "CT"
        ds.StudyDate = "20250101"
        ds.StudyTime = "120000"
        ds.Rows = 256
        ds.Columns = 256
        ds.BitsAllocated = 16
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.PixelData = b'\x00' * (256 * 256 * 2)  # 256x256 16-bit image
        
        # Set required attributes for saving
        ds.is_little_endian = True
        ds.is_implicit_VR = False
        
        # Add required file meta information
        ds.file_meta = Dataset()
        ds.file_meta.MediaStorageSOPClassUID = ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT Image Storage
        ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
        ds.file_meta.TransferSyntaxUID = "1.2.840.10008.1.2.1"  # Explicit VR Little Endian
        
        # Write to bytes
        buffer = io.BytesIO()
        ds.save_as(buffer, write_like_original=False)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    def test_upload_endpoint_accessible(self):
        """Test that the upload endpoint is accessible"""
        url = '/viewer/api/upload/'
        response = self.client.get(url)
        # Should return 405 Method Not Allowed for GET
        self.assertEqual(response.status_code, 405)
    
    def test_upload_with_valid_dicom(self):
        """Test uploading a valid DICOM file"""
        # Create test DICOM data
        dicom_data = self.create_test_dicom_file()
        
        # Create uploaded file
        uploaded_file = SimpleUploadedFile(
            "test.dcm",
            dicom_data,
            content_type="application/dicom"
        )
        
        # Make upload request
        url = '/viewer/api/upload/'
        response = self.client.post(url, {
            'files': uploaded_file
        })
        
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response content: {response.content.decode()}")
        
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check response content
        import json
        response_data = json.loads(response.content.decode())
        self.assertIn('uploaded_files', response_data)
        self.assertIn('study_id', response_data)
    
    def test_upload_without_files(self):
        """Test uploading without files"""
        url = '/viewer/api/upload/'
        response = self.client.post(url, {})
        
        print(f"Empty upload response status: {response.status_code}")
        print(f"Empty upload response content: {response.content.decode()}")
        
        # Should return 400 Bad Request
        self.assertEqual(response.status_code, 400)
    
    def test_csrf_token_handling(self):
        """Test CSRF token handling"""
        # Test without CSRF token
        client_no_csrf = Client(enforce_csrf_checks=True)
        client_no_csrf.login(username='testuser', password='testpass123')
        
        url = '/viewer/api/upload/'
        response = client_no_csrf.post(url, {})
        
        print(f"CSRF test response status: {response.status_code}")
        print(f"CSRF test response content: {response.content.decode()}")
        
        # Should handle CSRF properly (either 400 for no files or 403 for CSRF)
        self.assertIn(response.status_code, [400, 403])

def main():
    """Run the tests"""
    print("Testing DICOM upload functionality...")
    
    # Create test instance
    test = DicomUploadTest()
    test.setUp()
    
    print("\n1. Testing upload endpoint accessibility...")
    test.test_upload_endpoint_accessible()
    
    print("\n2. Testing upload with valid DICOM...")
    test.test_upload_with_valid_dicom()
    
    print("\n3. Testing upload without files...")
    test.test_upload_without_files()
    
    print("\n4. Testing CSRF token handling...")
    test.test_csrf_token_handling()
    
    print("\nAll tests completed!")

if __name__ == '__main__':
    main()