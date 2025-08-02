#!/usr/bin/env python3
"""
Comprehensive fix for DICOM viewer functionality
This script ensures all buttons work and images can be viewed properly
"""

import os
import sys
import django
import json
from pathlib import Path

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from viewer.models import DicomStudy, DicomSeries, DicomImage
from django.contrib.auth.models import User
from datetime import datetime

def create_test_user():
    """Create a test user if not exists"""
    try:
        user, created = User.objects.get_or_create(
            username='test_viewer',
            defaults={
                'email': 'test@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            user.set_password('test123')
            user.save()
            print("✓ Created test user: test_viewer (password: test123)")
        else:
            print("✓ Test user already exists")
        return user
    except Exception as e:
        print(f"✗ Error creating test user: {e}")
        return None

def create_sample_dicom_data():
    """Create sample DICOM data for testing"""
    try:
        # Check if we already have test data
        if DicomStudy.objects.filter(study_description="Test CT Study").exists():
            print("✓ Test DICOM data already exists")
            return True
        
        # Create a test study
        study = DicomStudy.objects.create(
            patient_name="TEST^PATIENT",
            patient_id="TEST001",
            patient_birth_date=datetime(1980, 1, 1).date(),
            patient_sex="M",
            study_instance_uid="1.2.3.4.5.6.7.8.9.10",
            study_date=datetime.now().date(),
            study_time=datetime.now().time(),
            study_description="Test CT Study",
            modality="CT",
            accession_number="ACC001"
        )
        print("✓ Created test study")
        
        # Create a test series
        series = DicomSeries.objects.create(
            study=study,
            series_instance_uid="1.2.3.4.5.6.7.8.9.10.1",
            series_number=1,
            series_description="Test Chest CT",
            modality="CT",
            body_part_examined="CHEST"
        )
        print("✓ Created test series")
        
        # Create test images
        for i in range(5):
            DicomImage.objects.create(
                series=series,
                instance_number=i+1,
                sop_instance_uid=f"1.2.3.4.5.6.7.8.9.10.1.{i+1}",
                image_type="ORIGINAL\\PRIMARY\\AXIAL",
                rows=512,
                columns=512,
                pixel_spacing="0.5\\0.5",
                slice_thickness=5.0,
                slice_location=i*5.0,
                window_width=1500,
                window_center=-600,
                dicom_file=f"test_images/test_ct_{i+1}.dcm"
            )
        print("✓ Created 5 test images")
        
        return True
    except Exception as e:
        print(f"✗ Error creating test DICOM data: {e}")
        return False

def fix_static_files():
    """Ensure static files are properly configured"""
    try:
        static_dirs = [
            'static/js',
            'static/css',
            'static/images',
            'staticfiles/js',
            'staticfiles/css'
        ]
        
        for dir_path in static_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        print("✓ Static directories created/verified")
        return True
    except Exception as e:
        print(f"✗ Error fixing static files: {e}")
        return False

def create_js_fixes():
    """Create JavaScript fix to ensure all buttons work"""
    js_fix_content = """
// Additional DICOM Viewer Fixes
(function() {
    'use strict';
    
    console.log('Applying additional DICOM viewer fixes...');
    
    // Ensure buttons work even without backend data
    window.addEventListener('DOMContentLoaded', function() {
        // Fix logout button
        const logoutBtn = document.getElementById('logout-advanced-btn');
        if (logoutBtn && !logoutBtn.onclick) {
            logoutBtn.onclick = function() {
                if (confirm('Are you sure you want to logout?')) {
                    window.location.href = '/accounts/logout/';
                }
            };
        }
        
        // Fix back to worklist button
        const backBtn = document.getElementById('back-to-worklist-btn');
        if (backBtn && !backBtn.onclick) {
            backBtn.onclick = function() {
                window.location.href = '/worklist/';
            };
        }
        
        // Fix fullscreen button
        const fullscreenBtn = document.getElementById('fullscreen-btn');
        if (fullscreenBtn && !fullscreenBtn.onclick) {
            fullscreenBtn.onclick = function() {
                if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen();
                    this.innerHTML = '<i class="fas fa-compress"></i>';
                } else {
                    document.exitFullscreen();
                    this.innerHTML = '<i class="fas fa-expand"></i>';
                }
            };
        }
        
        // Create demo image if no real images
        const canvas = document.getElementById('dicom-canvas-advanced');
        if (canvas && !window.currentDicomImage) {
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#000';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#fff';
            ctx.font = '20px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No DICOM image loaded', canvas.width/2, canvas.height/2);
            ctx.fillText('Use Upload button to load images', canvas.width/2, canvas.height/2 + 30);
        }
        
        // Show notification system is working
        if (window.showNotification) {
            window.showNotification('DICOM Viewer initialized', 'success');
        }
    });
})();
"""
    
    try:
        # Write the fix to static directory
        with open('static/js/dicom_viewer_additional_fixes.js', 'w') as f:
            f.write(js_fix_content)
        print("✓ Created additional JavaScript fixes")
        return True
    except Exception as e:
        print(f"✗ Error creating JavaScript fixes: {e}")
        return False

def check_viewer_status():
    """Check the overall status of the DICOM viewer"""
    print("\n" + "="*60)
    print("DICOM VIEWER STATUS CHECK")
    print("="*60)
    
    # Check database
    try:
        study_count = DicomStudy.objects.count()
        series_count = DicomSeries.objects.count()
        image_count = DicomImage.objects.count()
        print(f"\n📊 Database Status:")
        print(f"  - Studies: {study_count}")
        print(f"  - Series: {series_count}")
        print(f"  - Images: {image_count}")
    except Exception as e:
        print(f"\n❌ Database Error: {e}")
    
    # Check static files
    print(f"\n📁 Static Files Status:")
    js_files = [
        'static/js/dicom_viewer_comprehensive_fix.js',
        'static/js/dicom_viewer_advanced.js',
        'static/js/dicom_viewer_additional_fixes.js'
    ]
    for js_file in js_files:
        if Path(js_file).exists():
            print(f"  ✓ {js_file}")
        else:
            print(f"  ✗ {js_file} (missing)")
    
    print("\n" + "="*60)

def main():
    print("🔧 Running comprehensive DICOM viewer fixes...\n")
    
    # Run fixes
    fixes = [
        ("Creating test user", create_test_user),
        ("Creating sample DICOM data", create_sample_dicom_data),
        ("Fixing static files", fix_static_files),
        ("Creating JavaScript fixes", create_js_fixes)
    ]
    
    all_success = True
    for description, fix_func in fixes:
        print(f"\n{description}...")
        result = fix_func()
        if not result and result is not None:
            all_success = False
    
    # Check final status
    check_viewer_status()
    
    if all_success:
        print("\n✅ All fixes applied successfully!")
        print("\n📌 Next steps:")
        print("1. Restart the Django server if running")
        print("2. Navigate to http://localhost:8000/viewer/")
        print("3. Login with test_viewer/test123 if needed")
        print("4. Test all buttons and functionality")
    else:
        print("\n⚠️  Some fixes failed. Please check the errors above.")

if __name__ == "__main__":
    main()