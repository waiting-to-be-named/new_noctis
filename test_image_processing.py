#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomImage

def test_image_processing():
    """Test if image processing and base64 conversion works"""
    print("Testing image processing...")
    
    images = DicomImage.objects.all()
    print(f"Found {images.count()} images in database")
    
    for img in images:
        print(f"\nTesting image {img.id}: {img.file_path}")
        
        # Test pixel array loading
        try:
            pixel_array = img.get_pixel_array()
            if pixel_array is not None:
                print(f"✓ Pixel array loaded: {pixel_array.shape}")
            else:
                print("✗ Failed to load pixel array")
                continue
        except Exception as e:
            print(f"✗ Error loading pixel array: {e}")
            continue
        
        # Test windowing
        try:
            processed_array = img.apply_windowing(pixel_array, 400, 40, False)
            if processed_array is not None:
                print(f"✓ Windowing applied: {processed_array.shape}")
            else:
                print("✗ Failed to apply windowing")
                continue
        except Exception as e:
            print(f"✗ Error applying windowing: {e}")
            continue
        
        # Test base64 conversion
        try:
            base64_data = img.get_processed_image_base64(400, 40, False)
            if base64_data:
                print(f"✓ Base64 conversion successful")
                print(f"  Data length: {len(base64_data)} characters")
                print(f"  Starts with: {base64_data[:50]}...")
            else:
                print("✗ Failed to convert to base64")
        except Exception as e:
            print(f"✗ Error converting to base64: {e}")

if __name__ == "__main__":
    test_image_processing()