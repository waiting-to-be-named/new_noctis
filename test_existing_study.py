#!/usr/bin/env python3
"""
Test existing study and fix viewer functionality
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage
import requests

def test_existing_study():
    """Test the existing study and fix viewer functionality"""
    print("=== Testing Existing Study ===")
    
    try:
        # Get the existing study
        study = DicomStudy.objects.first()
        if not study:
            print("No studies found in database")
            return None
        
        print(f"Found study: {study}")
        print(f"  Patient: {study.patient_name}")
        print(f"  Series count: {study.series_count}")
        print(f"  Total images: {study.total_images}")
        
        # Check if there are any images
        if study.total_images == 0:
            print("No images found in study. Creating a test image...")
            
            # Create a test image for the existing study
            series = study.series.first()
            if not series:
                # Create a series if none exists
                series = DicomSeries.objects.create(
                    study=study,
                    series_instance_uid="1.2.3.4.5.6.7.8.9.11",
                    series_number=1,
                    series_description="Test Series",
                    modality="CT"
                )
                print(f"Created series: {series}")
            
            # Create a test image
            image = DicomImage.objects.create(
                series=series,
                sop_instance_uid="1.2.3.4.5.6.7.8.9.12",
                instance_number=1,
                file_path="dicom_files/test_image.dcm",
                rows=256,
                columns=256,
                bits_allocated=8,
                samples_per_pixel=1,
                photometric_interpretation="MONOCHROME2",
                pixel_spacing="1.0\\1.0",
                pixel_spacing_x=1.0,
                pixel_spacing_y=1.0,
                slice_thickness=1.0,
                window_center=40.0,
                window_width=400.0
            )
            print(f"Created test image: {image}")
        
        # Test API endpoints
        print("\n=== Testing API Endpoints ===")
        
        # Test get study images
        url = f"http://localhost:8000/viewer/api/studies/{study.id}/images/"
        response = requests.get(url)
        
        print(f"Get study images response status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            images = data.get('images', [])
            
            if images:
                print(f"Found {len(images)} images")
                
                # Test image data retrieval for each image
                for i, img_data in enumerate(images):
                    image_id = img_data['id']
                    print(f"\nTesting image {i+1}: {image_id}")
                    
                    url = f"http://localhost:8000/viewer/api/images/{image_id}/data/"
                    response = requests.get(url)
                    
                    print(f"  Image data response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('image_data'):
                            print(f"  ✓ Image {i+1} data retrieval successful")
                            print(f"  ✓ Viewer functionality working!")
                            return study.id
                        else:
                            print(f"  ✗ Image {i+1} no image data received")
                    else:
                        print(f"  ✗ Image {i+1} data retrieval failed: {response.text}")
                
                print("✗ No images returned valid data")
                return None
            else:
                print("✗ No images found in study")
                return None
        else:
            print(f"✗ Get study images API failed: {response.text}")
            return None
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    study_id = test_existing_study()
    if study_id:
        print(f"\n🎉 SUCCESS: Study {study_id} is working!")
    else:
        print("\n❌ FAILED: Issues remain with viewer functionality")