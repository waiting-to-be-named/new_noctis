#!/usr/bin/env python3
"""
Test script to verify image loading fixes
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/workspace')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomImage
from django.http import HttpRequest
from viewer.views import get_image_data
from rest_framework.test import APIRequestFactory
import json

def test_image_loading():
    """Test image loading functionality"""
    print("Testing image loading fixes...")
    
    # Get the first available image
    try:
        image = DicomImage.objects.first()
        if not image:
            print("No images found in database")
            return False
        
        print(f"Testing with image ID: {image.id}")
        
        # Test the enhanced processing method directly
        print("Testing get_enhanced_processed_image_base64...")
        result = image.get_enhanced_processed_image_base64()
        
        if result and result.strip():
            print(f"✓ Enhanced processing returned valid data (length: {len(result)})")
            if result.startswith('data:image/png;base64,'):
                print("✓ Data URL format is correct")
            else:
                print("⚠ Data URL format may be incorrect")
        else:
            print("✗ Enhanced processing returned empty or None data")
            return False
        
        # Test the API endpoint
        print("\nTesting API endpoint...")
        factory = APIRequestFactory()
        request = factory.get(f'/viewer/api/get-image-data/{image.id}/')
        
        # Mock the request user and other attributes
        request.user = None
        request.GET = {}
        
        try:
            response = get_image_data(request, image.id)
            print(f"✓ API endpoint returned status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.data
                if 'image_data' in data and data['image_data']:
                    print(f"✓ API returned valid image data (length: {len(data['image_data'])})")
                    return True
                else:
                    print("✗ API returned empty image data")
                    return False
            else:
                print(f"✗ API returned error status: {response.status_code}")
                if hasattr(response, 'data'):
                    print(f"Error details: {response.data}")
                return False
                
        except Exception as e:
            print(f"✗ API endpoint failed: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_synthetic_image_generation():
    """Test synthetic image generation"""
    print("\nTesting synthetic image generation...")
    
    try:
        image = DicomImage.objects.first()
        if not image:
            print("No images found for testing")
            return False
        
        result = image.generate_synthetic_image()
        
        if result and result.strip():
            print(f"✓ Synthetic image generation successful (length: {len(result)})")
            if result.startswith('data:image/png;base64,'):
                print("✓ Synthetic image has correct data URL format")
                return True
            else:
                print("⚠ Synthetic image format may be incorrect")
                return False
        else:
            print("✗ Synthetic image generation failed")
            return False
            
    except Exception as e:
        print(f"✗ Synthetic image test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Image Loading Fix Test ===")
    
    success1 = test_image_loading()
    success2 = test_synthetic_image_generation()
    
    print("\n=== Test Results ===")
    print(f"Image Loading: {'✓ PASS' if success1 else '✗ FAIL'}")
    print(f"Synthetic Generation: {'✓ PASS' if success2 else '✗ FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! Image loading should work correctly.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")