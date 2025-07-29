import os
from django.core.management.base import BaseCommand
from django.conf import settings
from viewer.models import DicomImage
from django.core.files.storage import default_storage

class Command(BaseCommand):
    help = 'Fix file paths in the database to work on current OS'

    def handle(self, *args, **options):
        self.stdout.write(f"Current MEDIA_ROOT: {settings.MEDIA_ROOT}")
        self.stdout.write(f"Current OS: {os.name}")
        
        # Get all images
        images = DicomImage.objects.all()
        total = images.count()
        fixed = 0
        errors = 0
        
        self.stdout.write(f"Checking {total} images...")
        
        for img in images:
            original_path = str(img.file_path)
            
            # Check if current path exists
            if default_storage.exists(original_path):
                continue
            
            # Try to fix the path
            fixed_path = None
            
            # Remove Windows drive letter and convert backslashes
            if ':' in original_path and len(original_path) > 2:
                # It's a Windows absolute path
                clean_path = original_path[2:].replace('\\', '/')
                if clean_path.startswith('/'):
                    clean_path = clean_path[1:]
                
                # Extract just the dicom_files/filename part
                if 'dicom_files' in clean_path:
                    idx = clean_path.find('dicom_files')
                    fixed_path = clean_path[idx:]
                else:
                    # Just use the filename
                    fixed_path = f"dicom_files/{os.path.basename(clean_path)}"
            
            # Try to find the file
            if fixed_path and default_storage.exists(fixed_path):
                img.file_path = fixed_path
                img.save()
                fixed += 1
                self.stdout.write(self.style.SUCCESS(f"Fixed: {original_path} -> {fixed_path}"))
            else:
                # Try to find file by basename
                basename = os.path.basename(original_path)
                test_path = f"dicom_files/{basename}"
                if default_storage.exists(test_path):
                    img.file_path = test_path
                    img.save()
                    fixed += 1
                    self.stdout.write(self.style.SUCCESS(f"Fixed: {original_path} -> {test_path}"))
                else:
                    errors += 1
                    self.stdout.write(self.style.ERROR(f"Could not fix: {original_path}"))
        
        self.stdout.write(self.style.SUCCESS(f"\nFixed {fixed} file paths"))
        if errors:
            self.stdout.write(self.style.WARNING(f"Could not fix {errors} file paths"))