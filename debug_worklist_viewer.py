#!/usr/bin/env python3
"""
Debug script to check the worklist-viewer connection issue
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomStudy, DicomImage, WorklistEntry, Facility
from django.contrib.auth.models import User

def debug_database():
    """Debug database contents"""
    print("=== Database Debug ===")
    
    # Check studies
    studies = DicomStudy.objects.all()
    print(f"Total studies: {studies.count()}")
    
    for study in studies[:3]:
        print(f"  Study: {study.patient_name} (ID: {study.id})")
        print(f"    Modality: {study.modality}")
        print(f"    Series count: {study.series_count}")
        print(f"    Total images: {study.total_images}")
        print()
    
    # Check images
    images = DicomImage.objects.all()
    print(f"Total images: {images.count()}")
    
    if images.exists():
        first_image = images.first()
        print(f"  First image: {first_image}")
        print(f"    File path: {first_image.file_path}")
        print(f"    File exists: {os.path.exists(str(first_image.file_path))}")
        print(f"    Series: {first_image.series}")
        print(f"    Study: {first_image.series.study if first_image.series else 'No series'}")
        print()
    
    # Check worklist entries
    entries = WorklistEntry.objects.all()
    print(f"Total worklist entries: {entries.count()}")
    
    for entry in entries[:3]:
        print(f"  Entry: {entry.patient_name} (ID: {entry.id})")
        print(f"    Status: {entry.status}")
        print(f"    Study: {entry.study}")
        print(f"    Accession: {entry.accession_number}")
        if entry.study:
            print(f"    Study images: {entry.study.total_images}")
        print()

def debug_file_system():
    """Debug file system"""
    print("=== File System Debug ===")
    
    # Check media directory
    media_dir = os.path.join(os.getcwd(), 'media')
    print(f"Media directory: {media_dir}")
    print(f"Media directory exists: {os.path.exists(media_dir)}")
    
    if os.path.exists(media_dir):
        dicom_dir = os.path.join(media_dir, 'dicom_files')
        print(f"DICOM directory: {dicom_dir}")
        print(f"DICOM directory exists: {os.path.exists(dicom_dir)}")
        
        if os.path.exists(dicom_dir):
            dicom_files = [f for f in os.listdir(dicom_dir) if f.endswith(('.dcm', '.dicom'))]
            print(f"Number of DICOM files: {len(dicom_files)}")
            
            if dicom_files:
                print("First 5 DICOM files:")
                for file in dicom_files[:5]:
                    file_path = os.path.join(dicom_dir, file)
                    file_size = os.path.getsize(file_path)
                    print(f"  {file} ({file_size} bytes)")
    
    # Check if any DICOM files are accessible
    images = DicomImage.objects.all()
    if images.exists():
        print("\nChecking DICOM file accessibility:")
        for image in images[:3]:
            file_path = str(image.file_path)
            exists = os.path.exists(file_path)
            print(f"  {file_path}: {'✓' if exists else '✗'}")
            
            if exists:
                try:
                    import pydicom
                    ds = pydicom.dcmread(file_path)
                    print(f"    Rows: {ds.Rows}, Columns: {ds.Columns}")
                except Exception as e:
                    print(f"    Error reading DICOM: {e}")

def debug_worklist_viewer_flow():
    """Debug the worklist to viewer flow"""
    print("=== Worklist to Viewer Flow Debug ===")
    
    # Find a worklist entry with a study
    entry = WorklistEntry.objects.filter(study__isnull=False).first()
    
    if not entry:
        print("No worklist entries with associated studies found")
        return
    
    print(f"Testing with worklist entry: {entry.patient_name}")
    print(f"  Entry ID: {entry.id}")
    print(f"  Study ID: {entry.study.id}")
    print(f"  Study patient: {entry.study.patient_name}")
    print(f"  Study images: {entry.study.total_images}")
    
    # Check if the study has images
    if entry.study.total_images == 0:
        print("  ⚠️  Study has no images!")
        return
    
    # Check if images are accessible
    images = DicomImage.objects.filter(series__study=entry.study)
    accessible_images = 0
    
    for image in images[:3]:
        if os.path.exists(str(image.file_path)):
            accessible_images += 1
        else:
            print(f"    ⚠️  Image file not found: {image.file_path}")
    
    print(f"  Accessible images: {accessible_images}/{images.count()}")

def main():
    """Main debug function"""
    print("=== Worklist-Viewer Issue Debug ===")
    print()
    
    debug_database()
    print()
    debug_file_system()
    print()
    debug_worklist_viewer_flow()
    print()
    
    print("=== Summary ===")
    print("If you see issues above, they may be causing the viewer to show no images.")
    print("Common issues:")
    print("1. Worklist entries without associated studies")
    print("2. Studies without images")
    print("3. DICOM files not accessible")
    print("4. Database inconsistencies")

if __name__ == "__main__":
    main()