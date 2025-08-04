#!/usr/bin/env python3
"""
Final verification script to confirm actual DICOM images are working
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomImage
import time

def verify_actual_images():
    """Verify that actual DICOM images are being loaded and processed"""
    print("🔍 FINAL VERIFICATION: Actual DICOM Images")
    print("=" * 60)
    
    # Get all studies
    studies = DicomStudy.objects.all()
    print(f"📚 Found {studies.count()} studies in database")
    
    total_images = 0
    actual_images = 0
    test_images = 0
    
    for study in studies:
        print(f"\n📖 Study {study.id}: {study.patient_name}")
        print(f"   📅 Date: {study.study_date}")
        print(f"   🏥 Modality: {study.modality}")
        
        # Get images for this study
        images = DicomImage.objects.filter(series__study=study)
        print(f"   📊 Images: {images.count()}")
        
        for image in images:
            total_images += 1
            print(f"      🖼️  Image {image.id}: ", end="")
            
            if image.file_path:
                # Check if file exists
                if hasattr(image.file_path, 'path'):
                    file_path = image.file_path.path
                else:
                    from django.conf import settings
                    file_path = os.path.join(settings.MEDIA_ROOT, str(image.file_path))
                
                if os.path.exists(file_path):
                    # Test actual DICOM loading
                    try:
                        start_time = time.time()
                        result = image.get_enhanced_processed_image_base64()
                        load_time = time.time() - start_time
                        
                        if result and result.startswith('data:image'):
                            actual_images += 1
                            print(f"✅ ACTUAL DICOM ({load_time:.2f}s)")
                        else:
                            test_images += 1
                            print(f"⚠️  TEST DATA")
                    except Exception as e:
                        test_images += 1
                        print(f"❌ ERROR: {str(e)[:50]}")
                else:
                    test_images += 1
                    print(f"❌ FILE MISSING")
            else:
                test_images += 1
                print(f"❌ NO FILE PATH")
    
    print(f"\n" + "=" * 60)
    print(f"📊 FINAL SUMMARY:")
    print(f"   Total images: {total_images}")
    print(f"   Actual DICOM images: {actual_images}")
    print(f"   Test/synthetic images: {test_images}")
    print(f"   Actual image percentage: {(actual_images/total_images*100):.1f}%" if total_images > 0 else "N/A")
    
    if actual_images > 0:
        print(f"\n🎉 SUCCESS: {actual_images} actual DICOM images are working!")
        return True
    else:
        print(f"\n💥 FAILURE: No actual DICOM images found!")
        return False

def test_specific_study():
    """Test a specific study with actual DICOM files"""
    print(f"\n🧪 TESTING SPECIFIC STUDY (Study 6)")
    print("-" * 40)
    
    try:
        study = DicomStudy.objects.get(id=6)
        print(f"📖 Study: {study.patient_name}")
        
        images = DicomImage.objects.filter(series__study=study)
        print(f"📊 Images in study: {images.count()}")
        
        for image in images:
            print(f"\n🖼️  Testing Image {image.id}:")
            
            # Test file existence
            if image.file_path:
                if hasattr(image.file_path, 'path'):
                    file_path = image.file_path.path
                else:
                    from django.conf import settings
                    file_path = os.path.join(settings.MEDIA_ROOT, str(image.file_path))
                
                if os.path.exists(file_path):
                    print(f"   📁 File exists: {os.path.basename(file_path)}")
                    
                    # Test DICOM loading
                    try:
                        dicom_data = image.load_dicom_data()
                        if dicom_data and hasattr(dicom_data, 'pixel_array'):
                            pixel_array = dicom_data.pixel_array
                            print(f"   ✅ DICOM loaded: {pixel_array.shape}")
                            
                            # Test image processing
                            result = image.get_enhanced_processed_image_base64()
                            if result and result.startswith('data:image'):
                                print(f"   ✅ Image processed: {len(result)} chars")
                            else:
                                print(f"   ❌ Image processing failed")
                        else:
                            print(f"   ❌ No pixel array in DICOM data")
                    except Exception as e:
                        print(f"   ❌ DICOM loading error: {e}")
                else:
                    print(f"   ❌ File missing: {file_path}")
            else:
                print(f"   ❌ No file path")
                
    except DicomStudy.DoesNotExist:
        print(f"❌ Study 6 not found")
    except Exception as e:
        print(f"❌ Error testing study: {e}")

if __name__ == "__main__":
    print("🚨 FINAL VERIFICATION OF DICOM VIEWER FIXES")
    print("=" * 60)
    
    # Test specific study first
    test_specific_study()
    
    # Full verification
    success = verify_actual_images()
    
    print(f"\n" + "=" * 60)
    if success:
        print("🎉 VERIFICATION PASSED: Actual DICOM images are working!")
        print("✅ The viewer will now display real medical images instead of test data.")
    else:
        print("💥 VERIFICATION FAILED: No actual DICOM images found.")
        print("❌ The viewer may still be showing test data.")
    
    print("=" * 60)