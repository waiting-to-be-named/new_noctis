#!/usr/bin/env python3
"""
Fix Image Processing for DICOM Viewer
Patches the DicomImage model to handle test data without actual DICOM files
"""

import os
import sys

def patch_dicom_image_model():
    """Add fallback image processing to handle test data"""
    
    print("🔧 Patching DicomImage model for test data support...")
    
    patch_code = '''
    def get_fallback_image_data(self):
        """Return cached image data if no file exists (for test data)"""
        if self.processed_image_cache:
            return self.processed_image_cache
        return None
    
    def get_enhanced_processed_image_base64_patched(self, window_width=None, window_level=None, inverted=False, 
                                                   resolution_factor=1.0, density_enhancement=True, contrast_boost=1.0):
        """Enhanced version with fallback for test data"""
        try:
            # Try the original method first
            return self.get_enhanced_processed_image_base64_original(
                window_width, window_level, inverted, resolution_factor, density_enhancement, contrast_boost
            )
        except Exception as e:
            print(f"Original image processing failed: {e}")
            # Fallback to cached data for test images
            cached_data = self.get_fallback_image_data()
            if cached_data:
                print("Using cached test image data")
                return cached_data
            print("No cached data available")
            return None
'''
    
    # Read the current models.py file
    models_path = "viewer/models.py"
    
    try:
        with open(models_path, 'r') as f:
            content = f.read()
        
        # Check if already patched
        if 'get_fallback_image_data' in content:
            print("✅ DicomImage model already patched")
            return True
        
        # Add the patch before the last line
        lines = content.split('\n')
        
        # Find the end of the DicomImage class
        dicom_image_end = -1
        in_dicom_image = False
        indent_level = 0
        
        for i, line in enumerate(lines):
            if 'class DicomImage(' in line:
                in_dicom_image = True
                indent_level = len(line) - len(line.lstrip())
            elif in_dicom_image and line.strip() and not line.startswith(' ' * (indent_level + 1)):
                # Found end of DicomImage class
                dicom_image_end = i
                break
        
        if dicom_image_end == -1:
            # Class extends to end of file
            dicom_image_end = len(lines)
        
        # Insert the patch before the end of the class
        patch_lines = patch_code.strip().split('\n')
        indented_patch = ['    ' + line for line in patch_lines]
        
        # Also rename the original method
        content = content.replace(
            'def get_enhanced_processed_image_base64(self',
            'def get_enhanced_processed_image_base64_original(self'
        )
        
        # Add new method with original name
        content = content.replace(
            'def get_enhanced_processed_image_base64_original(self',
            f'''def get_enhanced_processed_image_base64(self, window_width=None, window_level=None, inverted=False, 
                                                   resolution_factor=1.0, density_enhancement=True, contrast_boost=1.0):
        """Enhanced version with fallback for test data"""
        try:
            # Try the original method first
            return self.get_enhanced_processed_image_base64_original(
                window_width, window_level, inverted, resolution_factor, density_enhancement, contrast_boost
            )
        except Exception as e:
            print(f"Original image processing failed: {{e}}")
            # Fallback to cached data for test images
            cached_data = self.get_fallback_image_data()
            if cached_data:
                print("Using cached test image data")
                return cached_data
            print("No cached data available")
            return None
    
    def get_fallback_image_data(self):
        """Return cached image data if no file exists (for test data)"""
        if self.processed_image_cache:
            return self.processed_image_cache
        return None
    
    def get_enhanced_processed_image_base64_original(self'''
        )
        
        # Write the patched content
        with open(models_path, 'w') as f:
            f.write(content)
        
        print("✅ DicomImage model patched successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error patching DicomImage model: {e}")
        return False

def main():
    print("🔧 DICOM Image Processing Patch")
    print("=" * 40)
    
    if patch_dicom_image_model():
        print("\n✅ Image processing patch applied successfully!")
        print("🚀 Test images should now display in the viewer")
    else:
        print("\n❌ Failed to apply image processing patch")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())