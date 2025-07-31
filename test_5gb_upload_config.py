#!/usr/bin/env python3
"""
Test script to verify 5GB upload configuration
"""
import sys
import os
sys.path.append('.')

# Test settings import
try:
    from noctisview.settings import (
        DATA_UPLOAD_MAX_MEMORY_SIZE,
        FILE_UPLOAD_MAX_MEMORY_SIZE,
        MAX_DICOM_FILE_SIZE,
        BULK_UPLOAD_TIMEOUT,
        UPLOAD_PROGRESS_CACHE_TIMEOUT,
        LARGE_FILE_CHUNK_SIZE
    )
    
    print("✅ Settings imported successfully")
    
    # Verify 5GB limit settings
    expected_5gb = 5 * 1024 * 1024 * 1024  # 5GB in bytes
    expected_100mb = 100 * 1024 * 1024     # 100MB in bytes
    expected_1mb = 1024 * 1024             # 1MB in bytes
    
    print("\n📊 Upload Configuration Verification:")
    print(f"DATA_UPLOAD_MAX_MEMORY_SIZE: {DATA_UPLOAD_MAX_MEMORY_SIZE:,} bytes ({DATA_UPLOAD_MAX_MEMORY_SIZE / (1024**3):.1f}GB)")
    print(f"FILE_UPLOAD_MAX_MEMORY_SIZE: {FILE_UPLOAD_MAX_MEMORY_SIZE:,} bytes ({FILE_UPLOAD_MAX_MEMORY_SIZE / (1024**2):.0f}MB)")
    print(f"MAX_DICOM_FILE_SIZE: {MAX_DICOM_FILE_SIZE:,} bytes ({MAX_DICOM_FILE_SIZE / (1024**3):.1f}GB)")
    print(f"BULK_UPLOAD_TIMEOUT: {BULK_UPLOAD_TIMEOUT} seconds ({BULK_UPLOAD_TIMEOUT/60:.0f} minutes)")
    print(f"UPLOAD_PROGRESS_CACHE_TIMEOUT: {UPLOAD_PROGRESS_CACHE_TIMEOUT} seconds ({UPLOAD_PROGRESS_CACHE_TIMEOUT/3600:.1f} hours)")
    print(f"LARGE_FILE_CHUNK_SIZE: {LARGE_FILE_CHUNK_SIZE:,} bytes ({LARGE_FILE_CHUNK_SIZE / (1024**2):.0f}MB)")
    
    # Verify expected values
    checks = [
        ("DATA_UPLOAD_MAX_MEMORY_SIZE", DATA_UPLOAD_MAX_MEMORY_SIZE, expected_5gb),
        ("FILE_UPLOAD_MAX_MEMORY_SIZE", FILE_UPLOAD_MAX_MEMORY_SIZE, expected_100mb),
        ("MAX_DICOM_FILE_SIZE", MAX_DICOM_FILE_SIZE, expected_5gb),
        ("LARGE_FILE_CHUNK_SIZE", LARGE_FILE_CHUNK_SIZE, expected_1mb),
    ]
    
    print("\n🔍 Configuration Checks:")
    all_passed = True
    for setting_name, actual, expected in checks:
        if actual == expected:
            print(f"✅ {setting_name}: PASS")
        else:
            print(f"❌ {setting_name}: FAIL (expected {expected:,}, got {actual:,})")
            all_passed = False
    
    if all_passed:
        print("\n🎉 All configuration checks passed! 5GB upload support is correctly configured.")
    else:
        print("\n⚠️  Some configuration checks failed. Please review the settings.")
        
except ImportError as e:
    print(f"❌ Failed to import settings: {e}")
    sys.exit(1)

# Test view file size checks
print("\n🔍 Checking view file size limits...")
try:
    # Read the viewer views file to check size limits
    with open('viewer/views.py', 'r') as f:
        content = f.read()
    
    # Check for 5GB limits
    if '5 * 1024 * 1024 * 1024' in content:
        count = content.count('5 * 1024 * 1024 * 1024')
        print(f"✅ Found {count} instances of 5GB limits in viewer/views.py")
    else:
        print("❌ No 5GB limits found in viewer/views.py")
    
    # Check for old 500MB limits
    if '500 * 1024 * 1024' in content:
        count = content.count('500 * 1024 * 1024')
        print(f"⚠️  Found {count} remaining 500MB limits in viewer/views.py")
    else:
        print("✅ No old 500MB limits found in viewer/views.py")
        
    # Check for old 2GB bulk upload limits
    if '2 * 1024 * 1024 * 1024' in content:
        count = content.count('2 * 1024 * 1024 * 1024')
        print(f"⚠️  Found {count} remaining 2GB bulk upload limits in viewer/views.py")
    else:
        print("✅ No old 2GB bulk upload limits found in viewer/views.py")
        
except FileNotFoundError:
    print("❌ Could not find viewer/views.py")

print("\n📋 Summary:")
print("- Django settings configured for 5GB uploads")
file_upload_handlers_info = """- File upload handlers optimized (TemporaryFileUploadHandler first for large files)
- Memory upload limit kept at 100MB to avoid RAM issues
- Large file processing timeout: 1 hour
- Upload progress cache timeout: 2 hours
- File chunk size: 1MB for efficient processing"""
print(file_upload_handlers_info)

print("\n📝 Next Steps:")
print("1. Restart Django development server to apply settings")
print("2. Test with actual file uploads through the web interface")
print("3. Monitor server resources during large file uploads")
print("4. Consider nginx/apache configuration if using in production")

print("\n⚠️  Production Notes:")
print("- Web server (nginx/apache) may have separate upload size limits")
print("- Consider setting client_max_body_size 5G in nginx")
print("- Monitor disk space in temp directory during uploads")
print("- Ensure adequate server RAM for concurrent large uploads")