#!/usr/bin/env python3
"""
Debug script to test upload functionality and identify issues
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

from viewer.models import DicomStudy, WorklistEntry, Facility, DicomImage
from django.contrib.auth.models import User

def check_database():
    """Check the current state of the database"""
    print("=== Database Status ===")
    print(f"Studies: {DicomStudy.objects.count()}")
    print(f"Worklist entries: {WorklistEntry.objects.count()}")
    print(f"Facilities: {Facility.objects.count()}")
    print(f"Users: {User.objects.count()}")
    print(f"Images: {DicomImage.objects.count()}")
    
    if DicomStudy.objects.count() > 0:
        print("\n=== Recent Studies ===")
        for study in DicomStudy.objects.all()[:5]:
            print(f"  {study.patient_name} - {study.study_date} - {study.modality}")
            print(f"    ID: {study.id}, UID: {study.study_instance_uid}")
            print(f"    Series count: {study.series_count}")
            print(f"    Total images: {study.total_images}")
    
    if WorklistEntry.objects.count() > 0:
        print("\n=== Recent Worklist Entries ===")
        for entry in WorklistEntry.objects.all()[:5]:
            print(f"  {entry.patient_name} - {entry.accession_number} - {entry.status}")
            print(f"    Study: {entry.study.id if entry.study else 'None'}")
            print(f"    Facility: {entry.facility.name if entry.facility else 'None'}")

def check_media_files():
    """Check if media files exist"""
    print("\n=== Media Files ===")
    media_dir = Path("media")
    if media_dir.exists():
        print(f"Media directory exists: {media_dir}")
        dicom_dir = media_dir / "dicom_files"
        if dicom_dir.exists():
            files = list(dicom_dir.glob("*"))
            print(f"DICOM files found: {len(files)}")
            for file in files[:5]:
                print(f"  {file.name} ({file.stat().st_size} bytes)")
        else:
            print("DICOM directory does not exist")
    else:
        print("Media directory does not exist")

def check_worklist_consistency():
    """Check for consistency between studies and worklist entries"""
    print("\n=== Worklist Consistency ===")
    
    # Check for studies without worklist entries
    studies_without_entries = []
    for study in DicomStudy.objects.all():
        if not WorklistEntry.objects.filter(study=study).exists():
            studies_without_entries.append(study)
    
    if studies_without_entries:
        print(f"Studies without worklist entries: {len(studies_without_entries)}")
        for study in studies_without_entries[:3]:
            print(f"  {study.patient_name} (ID: {study.id})")
    else:
        print("All studies have worklist entries")
    
    # Check for worklist entries without studies
    entries_without_studies = WorklistEntry.objects.filter(study__isnull=True)
    if entries_without_studies.exists():
        print(f"Worklist entries without studies: {entries_without_studies.count()}")
        for entry in entries_without_studies[:3]:
            print(f"  {entry.patient_name} (ID: {entry.id})")
    else:
        print("All worklist entries have associated studies")

def check_image_accessibility():
    """Check if images can be accessed"""
    print("\n=== Image Accessibility ===")
    
    for image in DicomImage.objects.all()[:3]:
        print(f"Image {image.id}:")
        print(f"  File path: {image.file_path}")
        print(f"  File exists: {image.file_path.storage.exists(image.file_path.name) if image.file_path else False}")
        print(f"  Rows: {image.rows}, Columns: {image.columns}")
        
        # Try to load DICOM data
        try:
            dicom_data = image.load_dicom_data()
            if dicom_data:
                print(f"  DICOM data loaded successfully")
            else:
                print(f"  Failed to load DICOM data")
        except Exception as e:
            print(f"  Error loading DICOM data: {e}")

def main():
    """Run all checks"""
    print("Noctis DICOM System Debug Report")
    print("=" * 40)
    
    check_database()
    check_media_files()
    check_worklist_consistency()
    check_image_accessibility()
    
    print("\n=== Recommendations ===")
    print("1. If studies exist but worklist entries don't, check the upload process")
    print("2. If media files are missing, check file permissions and storage settings")
    print("3. If images can't be loaded, check DICOM file validity and dependencies")

if __name__ == "__main__":
    main()