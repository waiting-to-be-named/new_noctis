#!/usr/bin/env python3
import os
import sys
import django
import base64

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomImage
import numpy as np
from PIL import Image
import io

def generate_test_image_data(width=512, height=512, pattern_type='gradient'):
    """Generate test image data for demonstration"""
    
    if pattern_type == 'gradient':
        # Create a gradient pattern
        x = np.linspace(0, 1, width)
        y = np.linspace(0, 1, height)
        X, Y = np.meshgrid(x, y)
        data = (X + Y) * 127.5
    elif pattern_type == 'circles':
        # Create concentric circles
        x = np.linspace(-1, 1, width)
        y = np.linspace(-1, 1, height)
        X, Y = np.meshgrid(x, y)
        R = np.sqrt(X**2 + Y**2)
        data = np.sin(R * 10) * 127.5 + 127.5
    elif pattern_type == 'checkerboard':
        # Create checkerboard pattern
        block_size = 32
        data = np.zeros((height, width))
        for i in range(0, height, block_size):
            for j in range(0, width, block_size):
                if ((i // block_size) + (j // block_size)) % 2 == 0:
                    data[i:i+block_size, j:j+block_size] = 255
    else:
        # Random noise pattern
        data = np.random.randint(0, 256, (height, width))
    
    # Convert to uint8
    data = data.astype(np.uint8)
    
    # Create PIL image
    img = Image.fromarray(data, mode='L')
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return f"data:image/png;base64,{image_base64}"

def fix_test_images():
    """Fix test images that have missing files by ensuring they have cached data"""
    
    print("Fixing test images...")
    
    # Get all images
    images = DicomImage.objects.all()
    fixed_count = 0
    
    patterns = ['gradient', 'circles', 'checkerboard', 'noise']
    
    for idx, image in enumerate(images):
        print(f"\nChecking image {image.id}: {image.file_path}")
        
        # Check if file exists
        file_exists = False
        if image.file_path:
            if hasattr(image.file_path, 'path'):
                file_path = image.file_path.path
            else:
                file_path = os.path.join('media', str(image.file_path))
            
            file_exists = os.path.exists(file_path)
        
        if not file_exists:
            print(f"  File not found - checking cache...")
            
            # If no cache or empty cache, generate test data
            if not image.processed_image_cache or len(str(image.processed_image_cache)) < 100:
                print(f"  Generating test image data...")
                
                # Use different patterns for variety
                pattern = patterns[idx % len(patterns)]
                
                # Generate appropriate size based on stored dimensions
                width = image.columns or 512
                height = image.rows or 512
                
                test_data = generate_test_image_data(width, height, pattern)
                
                # Update the cache
                image.processed_image_cache = test_data
                image.save()
                
                print(f"  ✓ Generated {pattern} pattern test image ({width}x{height})")
                fixed_count += 1
            else:
                print(f"  ✓ Already has cached data")
        else:
            print(f"  ✓ File exists at {file_path}")
    
    print(f"\n{'='*60}")
    print(f"Fixed {fixed_count} images with missing files")
    print(f"Total images: {images.count()}")

if __name__ == "__main__":
    fix_test_images()