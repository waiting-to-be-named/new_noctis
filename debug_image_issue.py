#!/usr/bin/env python3
"""
Debug script to identify image data retrieval issues
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomImage
import pydicom
import numpy as np
from PIL import Image
import io
import base64

def debug_image_issue():
    """Debug the image data retrieval issue"""
    print("=== Debugging Image Data Retrieval ===")
    
    # Get the first image
    try:
        image = DicomImage.objects.first()
        if not image:
            print("No images found in database")
            return
        
        print(f"Testing image: {image}")
        print(f"File path: {image.file_path}")
        
        # Test DICOM loading
        print("\n1. Testing DICOM loading...")
        dicom_data = image.load_dicom_data()
        if dicom_data:
            print("✓ DICOM data loaded successfully")
            print(f"  Rows: {dicom_data.Rows}")
            print(f"  Columns: {dicom_data.Columns}")
            print(f"  Modality: {dicom_data.Modality}")
        else:
            print("✗ Failed to load DICOM data")
            return
        
        # Test pixel array
        print("\n2. Testing pixel array...")
        pixel_array = image.get_pixel_array()
        if pixel_array is not None:
            print("✓ Pixel array loaded successfully")
            print(f"  Shape: {pixel_array.shape}")
            print(f"  Data type: {pixel_array.dtype}")
            print(f"  Min value: {pixel_array.min()}")
            print(f"  Max value: {pixel_array.max()}")
        else:
            print("✗ Failed to load pixel array")
            return
        
        # Test windowing
        print("\n3. Testing windowing...")
        processed_array = image.apply_windowing(pixel_array)
        if processed_array is not None:
            print("✓ Windowing applied successfully")
            print(f"  Shape: {processed_array.shape}")
            print(f"  Data type: {processed_array.dtype}")
            print(f"  Min value: {processed_array.min()}")
            print(f"  Max value: {processed_array.max()}")
        else:
            print("✗ Failed to apply windowing")
            return
        
        # Test base64 conversion
        print("\n4. Testing base64 conversion...")
        try:
            # Convert to PIL Image
            pil_image = Image.fromarray(processed_array, mode='L')
            print("✓ PIL Image created successfully")
            
            # Convert to base64
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            print("✓ Base64 conversion successful")
            print(f"  Base64 length: {len(image_base64)}")
            
            # Test the full method
            base64_result = image.get_processed_image_base64()
            if base64_result:
                print("✓ Full get_processed_image_base64 successful")
                print(f"  Result starts with: {base64_result[:50]}...")
            else:
                print("✗ Full get_processed_image_base64 failed")
                
        except Exception as e:
            print(f"✗ Error in base64 conversion: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"Error in debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_image_issue()