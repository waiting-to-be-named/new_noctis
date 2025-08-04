#!/usr/bin/env python3
"""
Test script to verify DICOM image processing fix
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/workspace')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomImage
from django.contrib.auth.models import User

def test_dicom_image_processing():
    """Test DICOM image processing to verify the fix works"""
    try:
        # Get the first available DICOM image
        images = DicomImage.objects.all()
        if not images.exists():
            print("No DICOM images found in database")
            return False
        
        image = images.first()
        print(f"Testing image ID: {image.id}")
        print(f"Image file path: {image.file_path}")
        
        # Test the enhanced processing method
        print("Testing get_enhanced_processed_image_base64...")
        result = image.get_enhanced_processed_image_base64(
            window_width=1500,
            window_level=-600,
            inverted=False,
            resolution_factor=1.0,
            density_enhancement=True,
            contrast_boost=1.2
        )
        
        if result:
            print("✅ SUCCESS: Image processing completed successfully")
            print(f"Result length: {len(result)} characters")
            return True
        else:
            print("❌ FAILED: Image processing returned None")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_method_availability():
    """Test that the apply_diagnostic_quality_enhancement method exists"""
    try:
        images = DicomImage.objects.all()
        if not images.exists():
            print("No DICOM images found for method testing")
            return False
        
        image = images.first()
        
        # Check if the method exists
        if hasattr(image, 'apply_diagnostic_quality_enhancement'):
            print("✅ SUCCESS: apply_diagnostic_quality_enhancement method exists")
            
            # Test the method directly
            try:
                from PIL import Image
                import numpy as np
                
                # Create a test image
                test_array = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
                test_image = Image.fromarray(test_array, mode='L')
                
                result = image.apply_diagnostic_quality_enhancement(test_image)
                print("✅ SUCCESS: apply_diagnostic_quality_enhancement method works")
                return True
                
            except Exception as e:
                print(f"❌ ERROR testing method: {e}")
                return False
        else:
            print("❌ FAILED: apply_diagnostic_quality_enhancement method not found")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("Testing DICOM image processing fix...")
    print("=" * 50)
    
    # Test method availability
    print("\n1. Testing method availability...")
    method_test = test_method_availability()
    
    # Test full processing
    print("\n2. Testing full image processing...")
    processing_test = test_dicom_image_processing()
    
    print("\n" + "=" * 50)
    if method_test and processing_test:
        print("🎉 ALL TESTS PASSED: DICOM processing fix is working!")
    else:
        print("❌ SOME TESTS FAILED: Please check the errors above")
    
    print("\nTest completed.")