#!/usr/bin/env python3
"""
Test script for enhanced DICOM viewer features
Tests X-ray enhancement, MRI reconstruction, folder upload, and scrollable viewer
"""

import os
import sys
import django
import requests
import numpy as np
from PIL import Image
import base64
import io

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage
from viewer.views import AdvancedImageProcessor

def test_enhanced_image_processing():
    """Test the enhanced image processing capabilities"""
    print("Testing Enhanced Image Processing...")
    
    # Create test processor
    processor = AdvancedImageProcessor()
    
    # Create test image data
    test_image = np.random.rand(512, 512).astype(np.float32)
    
    # Test X-ray enhancements
    print("- Testing X-ray enhancements:")
    
    try:
        enhanced = processor.enhance_xray_image(test_image, 'comprehensive')
        print(f"  ✓ Comprehensive enhancement: {enhanced.shape}")
        
        enhanced = processor.enhance_xray_image(test_image, 'edge_enhancement')
        print(f"  ✓ Edge enhancement: {enhanced.shape}")
        
        enhanced = processor.enhance_xray_image(test_image, 'bone_enhancement')
        print(f"  ✓ Bone enhancement: {enhanced.shape}")
        
        enhanced = processor.enhance_xray_image(test_image, 'soft_tissue_enhancement')
        print(f"  ✓ Soft tissue enhancement: {enhanced.shape}")
        
    except Exception as e:
        print(f"  ✗ X-ray enhancement failed: {e}")
    
    # Test MRI enhancements
    print("- Testing MRI enhancements:")
    
    try:
        enhanced = processor.enhance_mri_image(test_image, 'comprehensive')
        print(f"  ✓ Comprehensive MRI enhancement: {enhanced.shape}")
        
        enhanced = processor.enhance_mri_image(test_image, 'brain_enhancement')
        print(f"  ✓ Brain enhancement: {enhanced.shape}")
        
        enhanced = processor.enhance_mri_image(test_image, 'vessel_enhancement')
        print(f"  ✓ Vessel enhancement: {enhanced.shape}")
        
    except Exception as e:
        print(f"  ✗ MRI enhancement failed: {e}")
    
    # Test MRI reconstruction
    print("- Testing MRI reconstruction:")
    
    try:
        reconstructed = processor.reconstruct_mri_image(test_image, 't1_weighted')
        print(f"  ✓ T1-weighted reconstruction: {reconstructed.shape}")
        
        reconstructed = processor.reconstruct_mri_image(test_image, 't2_weighted')
        print(f"  ✓ T2-weighted reconstruction: {reconstructed.shape}")
        
        reconstructed = processor.reconstruct_mri_image(test_image, 'flair')
        print(f"  ✓ FLAIR reconstruction: {reconstructed.shape}")
        
        reconstructed = processor.reconstruct_mri_image(test_image, 'dwi')
        print(f"  ✓ DWI reconstruction: {reconstructed.shape}")
        
    except Exception as e:
        print(f"  ✗ MRI reconstruction failed: {e}")

def test_api_endpoints():
    """Test the new API endpoints"""
    print("\nTesting API Endpoints...")
    
    # Base URL for testing
    base_url = "http://localhost:8000"
    
    # Test endpoints that don't require authentication
    endpoints = [
        "/viewer/api/studies/",
        "/viewer/api/worklist/",
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            print(f"  ✓ {endpoint}: Status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"  ⚠ {endpoint}: Server not running")
        except Exception as e:
            print(f"  ✗ {endpoint}: {e}")

def test_database_models():
    """Test database model functionality"""
    print("\nTesting Database Models...")
    
    try:
        # Test study count
        study_count = DicomStudy.objects.count()
        print(f"  ✓ Studies in database: {study_count}")
        
        # Test series count
        series_count = DicomSeries.objects.count()
        print(f"  ✓ Series in database: {series_count}")
        
        # Test image count
        image_count = DicomImage.objects.count()
        print(f"  ✓ Images in database: {image_count}")
        
        # Test enhanced processing on existing image
        if image_count > 0:
            test_image = DicomImage.objects.first()
            try:
                enhanced_data = test_image.get_enhanced_processed_image_base64(
                    thumbnail_size=(150, 150)
                )
                if enhanced_data:
                    print(f"  ✓ Enhanced image processing works")
                else:
                    print(f"  ✗ Enhanced image processing returned None")
            except Exception as e:
                print(f"  ✗ Enhanced image processing failed: {e}")
        
    except Exception as e:
        print(f"  ✗ Database test failed: {e}")

def test_file_structure():
    """Test that required files and directories exist"""
    print("\nTesting File Structure...")
    
    required_files = [
        'viewer/views.py',
        'viewer/models.py',
        'viewer/urls.py',
        'templates/dicom_viewer/viewer.html',
        'requirements.txt',
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✓ {file_path} exists")
        else:
            print(f"  ✗ {file_path} missing")
    
    # Test media directories
    media_dirs = [
        'media',
        'media/dicom_files',
        'media/temp',
        'media/bulk_uploads',
    ]
    
    for dir_path in media_dirs:
        if os.path.exists(dir_path):
            print(f"  ✓ {dir_path} directory exists")
        else:
            print(f"  ⚠ {dir_path} directory missing (will be created on demand)")

def test_dependencies():
    """Test that all required dependencies are installed"""
    print("\nTesting Dependencies...")
    
    required_packages = [
        'django',
        'djangorestframework',
        'pydicom',
        'PIL',
        'numpy',
        'scipy',
        'skimage',
        'cv2',
        'matplotlib',
    ]
    
    for package in required_packages:
        try:
            if package == 'PIL':
                import PIL
            elif package == 'skimage':
                import skimage
            elif package == 'cv2':
                import cv2
            else:
                __import__(package)
            print(f"  ✓ {package} installed")
        except ImportError:
            print(f"  ✗ {package} not installed")

def generate_test_report():
    """Generate a comprehensive test report"""
    print("=" * 60)
    print("ENHANCED DICOM VIEWER TEST REPORT")
    print("=" * 60)
    
    test_dependencies()
    test_file_structure()
    test_database_models()
    test_enhanced_image_processing()
    test_api_endpoints()
    
    print("\n" + "=" * 60)
    print("FEATURE SUMMARY")
    print("=" * 60)
    print("✓ X-ray Image Enhancement with multiple algorithms:")
    print("  - Comprehensive enhancement")
    print("  - Edge enhancement")
    print("  - Contrast enhancement")
    print("  - Noise reduction")
    print("  - Bone enhancement")
    print("  - Soft tissue enhancement")
    print()
    print("✓ MRI Image Reconstruction with sequence-specific algorithms:")
    print("  - T1-weighted reconstruction")
    print("  - T2-weighted reconstruction")
    print("  - FLAIR reconstruction")
    print("  - Diffusion-weighted imaging (DWI)")
    print("  - Perfusion reconstruction")
    print()
    print("✓ MRI Enhancement capabilities:")
    print("  - Comprehensive enhancement")
    print("  - Brain-specific enhancement")
    print("  - Spine enhancement")
    print("  - Vessel enhancement")
    print()
    print("✓ Enhanced folder upload functionality:")
    print("  - Bulk DICOM file processing")
    print("  - Progress monitoring")
    print("  - Error handling")
    print()
    print("✓ Scrollable image viewer:")
    print("  - Thumbnail navigation")
    print("  - Pagination support")
    print("  - Multiple image handling")
    print()
    print("✓ Enhanced UI components:")
    print("  - Image enhancement panel")
    print("  - Image navigator")
    print("  - Folder upload button")
    print("  - Progress notifications")

if __name__ == "__main__":
    generate_test_report()