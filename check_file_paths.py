import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import DicomImage, DicomStudy
from django.conf import settings

print("MEDIA_ROOT:", settings.MEDIA_ROOT)
print("Current OS:", sys.platform)
print()

# Check images
images = DicomImage.objects.all()[:10]
print(f"Total images in database: {DicomImage.objects.count()}")
print()

for img in images:
    print(f"Image ID: {img.id}")
    print(f"  Stored path: {img.file_path}")
    full_path = os.path.join(settings.MEDIA_ROOT, str(img.file_path))
    print(f"  Full path: {full_path}")
    print(f"  File exists: {os.path.exists(full_path)}")
    
    # Try different path variations
    if not os.path.exists(full_path):
        # Remove Windows drive letter if present
        clean_path = str(img.file_path)
        if ':' in clean_path and len(clean_path) > 2:
            clean_path = clean_path[2:].replace('\\', '/')
            if clean_path.startswith('/'):
                clean_path = clean_path[1:]
            test_path = os.path.join(settings.MEDIA_ROOT, clean_path)
            print(f"  Testing cleaned path: {test_path}")
            print(f"  Cleaned path exists: {os.path.exists(test_path)}")
        
        # Check if it's just the filename
        basename = os.path.basename(str(img.file_path))
        test_path2 = os.path.join(settings.MEDIA_ROOT, 'dicom_files', basename)
        print(f"  Testing basename path: {test_path2}")
        print(f"  Basename path exists: {os.path.exists(test_path2)}")
    print()

# List actual files in media directory
dicom_dir = os.path.join(settings.MEDIA_ROOT, 'dicom_files')
if os.path.exists(dicom_dir):
    files = os.listdir(dicom_dir)[:5]
    print(f"\nActual files in {dicom_dir}:")
    for f in files:
        print(f"  - {f}")