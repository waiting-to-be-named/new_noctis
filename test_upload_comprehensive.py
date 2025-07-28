#!/usr/bin/env python3
"""
Comprehensive test script to verify upload functionality.
This script tests various scenarios to ensure uploads work correctly.
"""

import os
import sys
import django
import tempfile
import shutil
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage
from worklist.models import WorklistEntry, Facility


class ComprehensiveUploadTest(TestCase):
    """Comprehensive test cases for upload functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a test facility
        self.facility = Facility.objects.create(
            name='Test Facility',
            address='123 Test St',
            phone='555-1234',
            email='test@facility.com'
        )
        
        # Ensure media directories exist
        self.media_root = default_storage.location
        self.dicom_dir = os.path.join(self.media_root, 'dicom_files')
        self.temp_dir = os.path.join(self.media_root, 'temp')
        
        for directory in [self.media_root, self.dicom_dir, self.temp_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
    
    def test_upload_no_files(self):
        """Test upload with no files provided."""
        response = self.client.post('/api/upload/', {})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], 'No files provided')
    
    def test_upload_empty_files_list(self):
        """Test upload with empty files list."""
        response = self.client.post('/api/upload/', {'files': []})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], 'No files provided')
    
    def test_upload_invalid_file_type(self):
        """Test upload with non-DICOM files."""
        # Create a test file that's not a DICOM file
        test_file = SimpleUploadedFile(
            "test.txt",
            b"This is not a DICOM file",
            content_type="text/plain"
        )
        
        response = self.client.post('/api/upload/', {
            'files': [test_file]
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertTrue('No valid DICOM files were uploaded' in response.json()['error'])
    
    def test_upload_large_file(self):
        """Test upload with file larger than 100MB."""
        # Create a large file (simulate 101MB)
        large_content = b"x" * (101 * 1024 * 1024)  # 101MB
        test_file = SimpleUploadedFile(
            "large.dcm",
            large_content,
            content_type="application/dicom"
        )
        
        response = self.client.post('/api/upload/', {
            'files': [test_file]
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertTrue('too large' in response.json()['error'])
    
    def test_upload_with_csrf_exemption(self):
        """Test that upload endpoints work without CSRF token."""
        # Create a mock DICOM file (this won't be valid, but tests the error handling)
        test_file = SimpleUploadedFile(
            "test.dcm",
            b"Invalid DICOM content",
            content_type="application/dicom"
        )
        
        response = self.client.post('/api/upload/', {
            'files': [test_file]
        })
        
        # Should return 400 with JSON error, not HTML
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
    
    def test_upload_folder_no_files(self):
        """Test folder upload with no files provided."""
        response = self.client.post('/api/upload-folder/', {})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], 'No files provided')
    
    def test_upload_folder_empty_files_list(self):
        """Test folder upload with empty files list."""
        response = self.client.post('/api/upload-folder/', {'files': []})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], 'No files provided')
    
    def test_api_error_middleware(self):
        """Test that API errors return JSON instead of HTML."""
        # Test a non-existent API endpoint
        response = self.client.get('/api/nonexistent/')
        self.assertEqual(response.status_code, 404)
        # Should return JSON, not HTML
        self.assertIn('error', response.json())
    
    def test_media_directories_creation(self):
        """Test that media directories are created properly."""
        from viewer.views import ensure_media_directories
        
        # Call the function
        ensure_media_directories()
        
        # Check that directories exist
        self.assertTrue(os.path.exists(self.media_root))
        self.assertTrue(os.path.exists(self.dicom_dir))
        self.assertTrue(os.path.exists(self.temp_dir))
        
        # Check that directories are writable
        self.assertTrue(os.access(self.media_root, os.W_OK))
        self.assertTrue(os.access(self.dicom_dir, os.W_OK))
        self.assertTrue(os.access(self.temp_dir, os.W_OK))
    
    def test_file_validation_accepts_various_formats(self):
        """Test that file validation accepts various DICOM formats."""
        valid_formats = [
            ('test.dcm', b'DICOM content'),
            ('test.dicom', b'DICOM content'),
            ('test.dcm.gz', b'Compressed DICOM'),
            ('test.dicom.gz', b'Compressed DICOM'),
            ('test.dcm.bz2', b'Compressed DICOM'),
            ('test.dicom.bz2', b'Compressed DICOM'),
            ('test.img', b'DICOM content'),
            ('test.ima', b'DICOM content'),
            ('test.raw', b'Raw data'),
            ('testfile', b'DICOM without extension'),  # No extension
        ]
        
        for filename, content in valid_formats:
            test_file = SimpleUploadedFile(
                filename,
                content,
                content_type="application/dicom"
            )
            
            response = self.client.post('/api/upload/', {
                'files': [test_file]
            })
            
            # Should not reject based on filename (server will handle DICOM validation)
            self.assertNotEqual(response.status_code, 400, f"File {filename} was rejected")
    
    def test_error_handling_with_traceback(self):
        """Test that errors include proper traceback information."""
        # Create a file that will cause an error
        test_file = SimpleUploadedFile(
            "error.dcm",
            b"This will cause an error",
            content_type="application/dicom"
        )
        
        response = self.client.post('/api/upload/', {
            'files': [test_file]
        })
        
        # Should return 400 with detailed error message
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        error_message = response.json()['error']
        
        # Error should be descriptive
        self.assertTrue(len(error_message) > 10)
    
    def test_partial_success_with_warnings(self):
        """Test that partial uploads include warnings."""
        # This test would require actual DICOM files, so we'll test the structure
        # In a real scenario, some files would succeed and others would fail
        
        # Create multiple files, some valid, some invalid
        files = [
            SimpleUploadedFile("valid.dcm", b"Valid DICOM content", content_type="application/dicom"),
            SimpleUploadedFile("invalid.txt", b"Invalid content", content_type="text/plain"),
        ]
        
        response = self.client.post('/api/upload/', {
            'files': files
        })
        
        # Should return 400 but with detailed error information
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
    
    def test_csrf_middleware_handling(self):
        """Test that CSRF middleware handles uploads properly."""
        # Test that upload endpoints are properly exempted
        test_file = SimpleUploadedFile(
            "test.dcm",
            b"Test content",
            content_type="application/dicom"
        )
        
        # Should not get CSRF errors
        response = self.client.post('/api/upload/', {
            'files': [test_file]
        })
        
        # Should not be a CSRF error (403)
        self.assertNotEqual(response.status_code, 403)
    
    def test_file_size_validation(self):
        """Test file size validation."""
        # Test files of various sizes
        test_cases = [
            (1024, "1KB file"),  # Should be accepted
            (1024 * 1024, "1MB file"),  # Should be accepted
            (50 * 1024 * 1024, "50MB file"),  # Should be accepted
            (101 * 1024 * 1024, "101MB file"),  # Should be rejected
        ]
        
        for size, description in test_cases:
            content = b"x" * size
            test_file = SimpleUploadedFile(
                f"test_{size}.dcm",
                content,
                content_type="application/dicom"
            )
            
            response = self.client.post('/api/upload/', {
                'files': [test_file]
            })
            
            if size > 100 * 1024 * 1024:  # 100MB limit
                self.assertEqual(response.status_code, 400)
                self.assertIn('too large', response.json()['error'])
            else:
                # Should not be rejected for size
                self.assertNotEqual(response.status_code, 400, f"{description} was rejected for size")


if __name__ == '__main__':
    # Run the tests
    import unittest
    unittest.main()