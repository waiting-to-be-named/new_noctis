#!/usr/bin/env python3
"""
Debug script to test worklist to viewer integration
"""

import os
import django
import sys

# Add the project directory to the Python path
sys.path.insert(0, '/workspace')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from worklist.models import WorklistEntry
from viewer.models import DicomStudy, DicomSeries, DicomImage
from django.contrib.auth.models import User

def debug_worklist_viewer_flow():
    """Debug the worklist to viewer flow"""
    
    print("\n=== Debugging Worklist to Viewer Flow ===\n")
    
    # Get the latest worklist entry
    entries = WorklistEntry.objects.all().order_by('-created_at')[:5]
    
    if not entries:
        print("No worklist entries found")
        return
    
    print(f"Found {entries.count()} recent worklist entries:\n")
    
    for entry in entries:
        print(f"Entry ID: {entry.id}")
        print(f"Patient Name: {entry.patient_name}")
        print(f"Study ID: {entry.study_id if entry.study else 'None'}")
        print(f"Status: {entry.status}")
        
        if entry.study:
            study = entry.study
            print(f"\n  Study Details:")
            print(f"  - Study ID: {study.id}")
            print(f"  - Study Instance UID: {study.study_instance_uid}")
            print(f"  - Study Date: {study.study_date}")
            print(f"  - Study Description: {study.study_description}")
            print(f"  - Patient Name: {study.patient_name}")
            
            # Check series
            series_list = study.series.all()
            print(f"  - Number of Series: {series_list.count()}")
            
            for series in series_list:
                print(f"\n    Series {series.series_number}:")
                print(f"    - Series ID: {series.id}")
                print(f"    - Description: {series.series_description}")
                print(f"    - Modality: {series.modality}")
                
                # Check images
                images = series.images.all()
                print(f"    - Number of Images: {images.count()}")
                
                if images:
                    # Check first image
                    first_image = images.first()
                    print(f"\n      First Image:")
                    print(f"      - Image ID: {first_image.id}")
                    print(f"      - Instance Number: {first_image.instance_number}")
                    print(f"      - Has DICOM file: {'Yes' if first_image.dicom_file else 'No'}")
                    if first_image.dicom_file:
                        print(f"      - File path: {first_image.dicom_file.path}")
                        print(f"      - File exists: {os.path.exists(first_image.dicom_file.path)}")
                    
                    # Test the viewer URL that would be generated
                    viewer_url = f"/viewer/study/{study.id}/"
                    print(f"\n    Viewer URL: {viewer_url}")
                    
                    # Test API endpoints
                    print(f"\n    API Endpoints to test:")
                    print(f"    - Study images: /viewer/api/get-study-images/{study.id}/")
                    print(f"    - Series list: /viewer/api/studies/{study.id}/series/")
                    print(f"    - Series images: /viewer/api/series/{series.id}/images/")
                    print(f"    - Image data: /viewer/api/images/{first_image.id}/data/")
        
        print("\n" + "-"*50 + "\n")
    
    # Check for orphaned studies (studies without worklist entries)
    orphaned_studies = DicomStudy.objects.filter(worklist_entries__isnull=True)
    if orphaned_studies:
        print(f"\nFound {orphaned_studies.count()} orphaned studies (without worklist entries)")
        for study in orphaned_studies[:5]:
            print(f"  - Study ID: {study.id}, Patient: {study.patient_name}, Date: {study.study_date}")

if __name__ == "__main__":
    debug_worklist_viewer_flow()