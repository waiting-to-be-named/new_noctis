#!/usr/bin/env python3
"""
Test script to verify upload error handling improvements.
This script tests various error scenarios to ensure proper JSON responses.
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage
from worklist.models import WorklistEntry, Facility


class UploadErrorHandlingTest(TestCase):
    """Test cases for upload error handling."""
    
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
    
    def test_upload_no_files(self):
        """Test upload with no files provided."""
        response = self.client.post('/api/upload/', {})
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
        self.assertEqual(response.json()['error'], 'No valid DICOM files were uploaded')
    
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
    
    def test_api_error_middleware(self):
        """Test that API errors return JSON instead of HTML."""
        # Test a non-existent API endpoint
        response = self.client.get('/api/nonexistent/')
        self.assertEqual(response.status_code, 404)
        # Should return JSON, not HTML
        self.assertIn('error', response.json())


if __name__ == '__main__':
    # Run the tests
    import unittest
    unittest.main()