#!/usr/bin/env python
"""
Create test DICOM data for the viewer
"""

import os
import sys
import django
import numpy as np
from datetime import datetime, timedelta
import random

# Setup Django environment
sys.path.append('/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctis.settings')
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage
from django.contrib.auth.models import User

def create_test_data():
    """Create test DICOM studies with synthetic data"""
    print("Creating test DICOM data...")
    
    # Get or create test user
    try:
        user = User.objects.get(username='admin')
    except User.DoesNotExist:
        user = User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        print("Created admin user (username: admin, password: admin)")
    
    # Create test studies
    test_patients = [
        {
            'patient_name': 'John Doe',
            'patient_id': 'TEST001',
            'patient_birth_date': '1980-01-15',
            'patient_sex': 'M',
            'studies': [
                {
                    'study_description': 'Chest CT - Routine',
                    'modality': 'CT',
                    'series': [
                        {
                            'series_description': 'Axial Chest',
                            'body_part': 'CHEST',
                            'num_images': 50
                        },
                        {
                            'series_description': 'Coronal Reconstruction',
                            'body_part': 'CHEST',
                            'num_images': 30
                        }
                    ]
                }
            ]
        },
        {
            'patient_name': 'Jane Smith',
            'patient_id': 'TEST002',
            'patient_birth_date': '1975-06-20',
            'patient_sex': 'F',
            'studies': [
                {
                    'study_description': 'Brain MRI - Contrast',
                    'modality': 'MR',
                    'series': [
                        {
                            'series_description': 'T1 Weighted',
                            'body_part': 'HEAD',
                            'num_images': 25
                        },
                        {
                            'series_description': 'T2 Weighted',
                            'body_part': 'HEAD',
                            'num_images': 25
                        },
                        {
                            'series_description': 'FLAIR',
                            'body_part': 'HEAD',
                            'num_images': 20
                        }
                    ]
                }
            ]
        },
        {
            'patient_name': 'Bob Johnson',
            'patient_id': 'TEST003',
            'patient_birth_date': '1990-03-10',
            'patient_sex': 'M',
            'studies': [
                {
                    'study_description': 'Abdomen CT - Contrast',
                    'modality': 'CT',
                    'series': [
                        {
                            'series_description': 'Arterial Phase',
                            'body_part': 'ABDOMEN',
                            'num_images': 40
                        },
                        {
                            'series_description': 'Venous Phase',
                            'body_part': 'ABDOMEN',
                            'num_images': 40
                        }
                    ]
                }
            ]
        }
    ]
    
    created_studies = []
    
    for patient_data in test_patients:
        for study_data in patient_data['studies']:
            # Create study
            study_date = datetime.now() - timedelta(days=random.randint(1, 30))
            
            study = DicomStudy.objects.create(
                patient_name=patient_data['patient_name'],
                patient_id=patient_data['patient_id'],
                patient_birth_date=patient_data['patient_birth_date'],
                patient_sex=patient_data['patient_sex'],
                study_date=study_date.date(),
                study_time=study_date.time(),
                study_description=study_data['study_description'],
                study_instance_uid=f"1.2.3.4.5.{random.randint(1000, 9999)}",
                accession_number=f"ACC{random.randint(10000, 99999)}",
                institution_name="Test Hospital",
                uploaded_by=user
            )
            
            created_studies.append(study)
            print(f"Created study: {study.study_description} for {study.patient_name}")
            
            # Create series for each study
            series_number = 1
            for series_data in study_data['series']:
                series = DicomSeries.objects.create(
                    study=study,
                    series_number=series_number,
                    series_instance_uid=f"1.2.3.4.6.{random.randint(1000, 9999)}",
                    series_description=series_data['series_description'],
                    modality=study_data['modality'],
                    body_part_examined=series_data['body_part'],
                    series_date=study_date.date(),
                    series_time=study_date.time()
                )
                
                print(f"  Created series: {series.series_description}")
                
                # Create images for each series
                for i in range(series_data['num_images']):
                    # Generate synthetic image data
                    rows, columns = 512, 512
                    
                    # Window/level settings based on modality and body part
                    if study_data['modality'] == 'CT':
                        if series_data['body_part'] == 'CHEST':
                            window_width, window_center = 1500, -600
                        elif series_data['body_part'] == 'ABDOMEN':
                            window_width, window_center = 350, 40
                        else:
                            window_width, window_center = 400, 40
                    else:  # MR
                        window_width, window_center = 255, 127
                    
                    image = DicomImage.objects.create(
                        series=series,
                        instance_number=i + 1,
                        sop_instance_uid=f"1.2.3.4.7.{random.randint(10000, 99999)}",
                        rows=rows,
                        columns=columns,
                        pixel_spacing_x=1.0,
                        pixel_spacing_y=1.0,
                        slice_thickness=5.0 if study_data['modality'] == 'CT' else 3.0,
                        window_width=window_width,
                        window_center=window_center,
                        file_path=f"test_data/{study.id}/{series.id}/image_{i+1}.dcm"
                    )
                    
                    # Set test image data flag
                    image.test_data = True
                    image.save()
                
                print(f"    Created {series_data['num_images']} images")
                
                series_number += 1
    
    print(f"\nSuccessfully created {len(created_studies)} test studies!")
    print("\nYou can now log in with:")
    print("  Username: admin")
    print("  Password: admin")
    
    return created_studies

if __name__ == '__main__':
    create_test_data()