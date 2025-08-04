#!/usr/bin/env python3
"""
Test script to verify actual DICOM images are being loaded
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomImage
import pydicom
import numpy as np
from PIL import Image
import io
import base64

def test_actual_image_loading():
    """Test that actual DICOM images can be loaded and processed"""
    print("🧪 Testing actual DICOM image loading...")
    
    # Get images with actual files
    images = DicomImage.objects.filter(file_path__isnull=False)[:3]
    
    for image in images:
        try:
            print(f"\n📸 Testing image {image.id}...")
            
            # Test 1: Load DICOM data
            print(f"  Step 1: Loading DICOM data...")
            dicom_data = image.load_dicom_data()
            if dicom_data and hasattr(dicom_data, 'pixel_array'):
                pixel_array = dicom_data.pixel_array
                print(f"  ✅ DICOM data loaded, shape: {pixel_array.shape}")
            else:
                print(f"  ❌ Failed to load DICOM data")
                continue
            
            # Test 2: Get pixel array
            print(f"  Step 2: Getting pixel array...")
            pixel_array = image.get_pixel_array()
            if pixel_array is not None:
                print(f"  ✅ Pixel array obtained, shape: {pixel_array.shape}")
            else:
                print(f"  ❌ Failed to get pixel array")
                continue
            
            # Test 3: Process image
            print(f"  Step 3: Processing image...")
            result = image.get_enhanced_processed_image_base64()
            if result and result.startswith('data:image'):
                print(f"  ✅ Image processed successfully")
                print(f"  📊 Base64 length: {len(result)} characters")
            else:
                print(f"  ❌ Failed to process image")
            
        except Exception as e:
            print(f"  ❌ Error testing image {image.id}: {e}")

def test_study_images():
    """Test that study images are accessible"""
    print("\n📚 Testing study images...")
    
    from viewer.models import DicomStudy
    
    studies = DicomStudy.objects.all()[:2]
    
    for study in studies:
        try:
            print(f"\n📖 Testing study {study.id} ({study.patient_name})...")
            
            # Get images for this study
            images = DicomImage.objects.filter(series__study=study)
            print(f"  📊 Found {images.count()} images in study")
            
            # Test first image
            if images.exists():
                first_image = images.first()
                print(f"  🖼️  Testing first image {first_image.id}...")
                
                result = first_image.get_enhanced_processed_image_base64()
                if result and result.startswith('data:image'):
                    print(f"  ✅ First image processed successfully")
                else:
                    print(f"  ❌ First image processing failed")
            
        except Exception as e:
            print(f"  ❌ Error testing study {study.id}: {e}")

if __name__ == "__main__":
    print("🚨 TESTING ACTUAL DICOM IMAGE LOADING")
    print("=" * 50)
    
    test_actual_image_loading()
    test_study_images()
    
    print("\n" + "=" * 50)
    print("✅ Testing completed!")