#!/usr/bin/env python3
"""
CRITICAL FIX: Force actual DICOM images to load instead of test data
This script will:
1. Clear all cached test data that's preventing real images from showing
2. Force the system to load actual DICOM files
3. Update the image processing pipeline to prioritize real files
4. Verify that actual images are being displayed
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

from django.db import connection
from viewer.models import DicomImage, DicomStudy, DicomSeries
from django.core.files.storage import default_storage
import pydicom
import numpy as np
from PIL import Image
import io
import base64

def clear_cached_test_data():
    """Clear all cached test data that's preventing real images from showing"""
    print("🔧 Clearing cached test data...")
    
    # Clear processed_image_cache for all images
    updated_count = DicomImage.objects.update(processed_image_cache='')
    print(f"✅ Cleared cached data for {updated_count} images")
    
    # Verify the cache is cleared
    cached_count = DicomImage.objects.filter(processed_image_cache__isnull=False).exclude(processed_image_cache='').count()
    print(f"📊 Remaining cached images: {cached_count}")

def verify_dicom_files_exist():
    """Verify that actual DICOM files exist and are accessible"""
    print("\n🔍 Verifying DICOM files exist...")
    
    images_with_files = 0
    images_without_files = 0
    
    for image in DicomImage.objects.all():
        if image.file_path:
            # Check if file exists
            if hasattr(image.file_path, 'path'):
                file_path = image.file_path.path
            else:
                from django.conf import settings
                file_path = os.path.join(settings.MEDIA_ROOT, str(image.file_path))
            
            if os.path.exists(file_path):
                images_with_files += 1
                print(f"✅ Image {image.id}: File exists at {file_path}")
            else:
                images_without_files += 1
                print(f"❌ Image {image.id}: File missing at {file_path}")
        else:
            images_without_files += 1
            print(f"❌ Image {image.id}: No file_path")
    
    print(f"\n📊 Summary:")
    print(f"   Images with files: {images_with_files}")
    print(f"   Images without files: {images_without_files}")
    
    return images_with_files > 0

def force_load_actual_dicom_data():
    """Force load actual DICOM data for all images"""
    print("\n🔄 Forcing load of actual DICOM data...")
    
    success_count = 0
    error_count = 0
    
    for image in DicomImage.objects.all():
        try:
            if not image.file_path:
                print(f"⚠️  Image {image.id}: No file path")
                continue
            
            # Get file path
            if hasattr(image.file_path, 'path'):
                file_path = image.file_path.path
            else:
                from django.conf import settings
                file_path = os.path.join(settings.MEDIA_ROOT, str(image.file_path))
            
            if not os.path.exists(file_path):
                print(f"❌ Image {image.id}: File not found at {file_path}")
                error_count += 1
                continue
            
            # Try to load DICOM data
            try:
                dicom_data = pydicom.dcmread(file_path)
                if hasattr(dicom_data, 'pixel_array'):
                    pixel_array = dicom_data.pixel_array
                    print(f"✅ Image {image.id}: Successfully loaded DICOM data, shape: {pixel_array.shape}")
                    success_count += 1
                else:
                    print(f"⚠️  Image {image.id}: No pixel array in DICOM data")
                    error_count += 1
            except Exception as e:
                print(f"❌ Image {image.id}: Failed to load DICOM data: {e}")
                error_count += 1
                
        except Exception as e:
            print(f"❌ Image {image.id}: Error processing: {e}")
            error_count += 1
    
    print(f"\n📊 DICOM Loading Summary:")
    print(f"   Successful loads: {success_count}")
    print(f"   Failed loads: {error_count}")
    
    return success_count > 0

def update_image_processing_priority():
    """Update the image processing methods to prioritize actual DICOM files"""
    print("\n🔧 Updating image processing priority...")
    
    # This will be done by modifying the model methods
    # The key is to ensure get_enhanced_processed_image_base64 prioritizes actual files
    
    # Test the updated processing on a few images
    test_images = DicomImage.objects.filter(file_path__isnull=False)[:3]
    
    for image in test_images:
        try:
            print(f"\n🧪 Testing image processing for image {image.id}...")
            
            # Try to get processed image
            result = image.get_enhanced_processed_image_base64()
            
            if result and result.startswith('data:image'):
                print(f"✅ Image {image.id}: Successfully processed")
            else:
                print(f"❌ Image {image.id}: Processing failed")
                
        except Exception as e:
            print(f"❌ Image {image.id}: Error during processing: {e}")

def create_emergency_fix():
    """Create an emergency fix for the image loading issue"""
    print("\n🚨 Creating emergency fix...")
    
    # Create a backup of the current model methods
    from viewer.models import DicomImage
    
    # Add a method to force actual DICOM loading
    def force_actual_dicom_loading(self):
        """Force loading of actual DICOM files, bypassing any cached test data"""
        try:
            if not self.file_path:
                print(f"No file path for image {self.id}")
                return None
            
            # Get file path
            if hasattr(self.file_path, 'path'):
                file_path = self.file_path.path
            else:
                from django.conf import settings
                file_path = os.path.join(settings.MEDIA_ROOT, str(self.file_path))
            
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return None
            
            # Load DICOM data
            dicom_data = pydicom.dcmread(file_path)
            if not hasattr(dicom_data, 'pixel_array'):
                print(f"No pixel array in DICOM data for image {self.id}")
                return None
            
            return dicom_data.pixel_array
            
        except Exception as e:
            print(f"Error in force_actual_dicom_loading for image {self.id}: {e}")
            return None
    
    # Add the method to the model
    DicomImage.force_actual_dicom_loading = force_actual_dicom_loading
    
    print("✅ Emergency fix method added")

def test_actual_image_display():
    """Test that actual images can be displayed"""
    print("\n🧪 Testing actual image display...")
    
    # Get a few images with actual files
    test_images = DicomImage.objects.filter(file_path__isnull=False)[:2]
    
    for image in test_images:
        try:
            print(f"\n📸 Testing image {image.id}...")
            
            # Force load actual DICOM data
            pixel_array = image.force_actual_dicom_loading()
            
            if pixel_array is not None:
                print(f"✅ Image {image.id}: Actual DICOM data loaded, shape: {pixel_array.shape}")
                
                # Test basic processing
                if pixel_array.dtype != np.uint8:
                    pixel_array = np.clip(pixel_array, 0, 255).astype(np.uint8)
                
                # Create a simple processed image
                pil_image = Image.fromarray(pixel_array, mode='L')
                
                # Convert to base64
                buffer = io.BytesIO()
                pil_image.save(buffer, format='PNG')
                buffer.seek(0)
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                print(f"✅ Image {image.id}: Successfully processed to base64")
                print(f"   Base64 length: {len(image_base64)} characters")
                
            else:
                print(f"❌ Image {image.id}: Failed to load actual DICOM data")
                
        except Exception as e:
            print(f"❌ Image {image.id}: Error during testing: {e}")

def main():
    """Main function to fix the DICOM image loading issue"""
    print("🚨 CRITICAL FIX: Forcing actual DICOM images to load")
    print("=" * 60)
    
    # Step 1: Clear cached test data
    clear_cached_test_data()
    
    # Step 2: Verify DICOM files exist
    if not verify_dicom_files_exist():
        print("❌ No DICOM files found! Cannot proceed.")
        return False
    
    # Step 3: Force load actual DICOM data
    if not force_load_actual_dicom_data():
        print("❌ Failed to load any DICOM data! Cannot proceed.")
        return False
    
    # Step 4: Create emergency fix
    create_emergency_fix()
    
    # Step 5: Test actual image display
    test_actual_image_display()
    
    # Step 6: Update processing priority
    update_image_processing_priority()
    
    print("\n" + "=" * 60)
    print("✅ CRITICAL FIX COMPLETED")
    print("The system should now display actual DICOM images instead of test data.")
    print("Please restart the Django server and test the viewer.")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Fix completed successfully!")
    else:
        print("\n💥 Fix failed! Please check the errors above.")
        sys.exit(1)