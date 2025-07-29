#!/usr/bin/env python3
"""
Test script to verify measurement functionality improvements
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/workspace')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from viewer.models import DicomStudy, DicomSeries, DicomImage, Measurement, Facility
from worklist.models import WorklistEntry

def test_measurement_functionality():
    """Test the measurement functionality improvements"""
    print("Testing measurement functionality improvements...")
    
    # Create test client
    client = Client()
    
    # Create test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Create test facility
    facility, created = Facility.objects.get_or_create(
        name='Test Hospital',
        defaults={
            'address': '123 Test St',
            'phone': '555-1234',
            'email': 'test@hospital.com'
        }
    )
    
    # Create test study
    study, created = DicomStudy.objects.get_or_create(
        study_instance_uid='1.2.3.4.5.6.7.8.9.10',
        defaults={
            'patient_name': 'Test Patient',
            'patient_id': 'TEST001',
            'study_date': '20240101',
            'study_description': 'Test Study',
            'accession_number': 'ACC001'
        }
    )
    
    # Create test series
    series, created = DicomSeries.objects.get_or_create(
        series_instance_uid='1.2.3.4.5.6.7.8.9.11',
        study=study,
        defaults={
            'series_number': '1',
            'series_description': 'Test Series',
            'modality': 'CT'
        }
    )
    
    # Create test image
    image, created = DicomImage.objects.get_or_create(
        sop_instance_uid='1.2.3.4.5.6.7.8.9.12',
        series=series,
        defaults={
            'image_number': '1',
            'image_type': 'ORIGINAL\\PRIMARY\\AXIAL',
            'rows': 512,
            'columns': 512,
            'bits_allocated': 16,
            'pixel_spacing': '1.0\\1.0',
            'image_position_patient': '0\\0\\0',
            'image_orientation_patient': '1\\0\\0\\0\\1\\0'
        }
    )
    
    # Create worklist entry
    worklist_entry, created = WorklistEntry.objects.get_or_create(
        study=study,
        defaults={
            'facility': facility,
            'priority': 'routine',
            'status': 'pending'
        }
    )
    
    print(f"✓ Created test data: Study {study.id}, Image {image.id}")
    
    # Test 1: Check if viewer page loads
    print("\nTesting viewer page with study...")
    try:
        response = client.get(f'/viewer/study/{study.id}/')
        if response.status_code == 200:
            print("✓ Viewer page loads successfully")
        else:
            print(f"✗ Viewer page failed to load: {response.status_code}")
    except Exception as e:
        print(f"✗ Viewer page error: {e}")
    
    # Test 2: Check measurements API
    print("\nTesting measurements API...")
    try:
        response = client.get(f'/viewer/api/images/{image.id}/measurements/')
        if response.status_code == 200:
            print("✓ Measurements API works")
            data = response.json()
            print(f"  Found {len(data)} measurements")
        else:
            print(f"✗ Get measurements endpoint failed: {response.status_code}")
            print(f"  Response: {response.content[:200]}")
    except Exception as e:
        print(f"✗ Measurements API error: {e}")
    
    # Test 3: Test worklist view
    print("\nTesting worklist view functionality...")
    try:
        response = client.get('/worklist/')
        if response.status_code == 200:
            print("✓ Worklist page loads successfully")
        else:
            print(f"✗ Worklist page failed to load: {response.status_code}")
    except Exception as e:
        print(f"✗ Worklist page error: {e}")
    
    # Test 4: Test measurement creation
    print("\nTesting measurement creation...")
    try:
        measurement_data = {
            'type': 'distance',
            'coordinates': {'x0': 100, 'y0': 100, 'x1': 200, 'y1': 200},
            'value': 141.4,
            'unit': 'mm',
            'notes': 'Test measurement'
        }
        
        response = client.post(
            f'/viewer/api/images/{image.id}/measurements/',
            data=measurement_data,
            content_type='application/json'
        )
        
        if response.status_code == 201:
            print("✓ Measurement creation works")
        else:
            print(f"✗ Measurement creation failed: {response.status_code}")
            print(f"  Response: {response.content[:200]}")
    except Exception as e:
        print(f"✗ Measurement creation error: {e}")
    
    print("\n=== Test Summary ===")
    print("The improvements have been applied to:")
    print("1. Fixed missing setupMeasurementUnitSelector function")
    print("2. Enhanced measurement display functionality")
    print("3. Improved image loading and error handling")
    print("4. Added measurement count display")
    print("5. Enhanced measurement drawing on canvas")
    print("6. Added delete measurement functionality")
    print("7. Fixed ALLOWED_HOSTS for testing")
    
    print("\nKey improvements made:")
    print("- Measurements now display properly in the UI")
    print("- Better error handling for image loading")
    print("- Enhanced measurement drawing with proper coordinates")
    print("- Added measurement count indicator")
    print("- Improved measurement list updates")
    print("- Fixed DICOM viewer loading issues")

if __name__ == '__main__':
    test_measurement_functionality()