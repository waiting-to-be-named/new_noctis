#!/usr/bin/env python3
"""Test script to verify DICOM viewer image quality fixes"""

import os

def test_javascript_fixes():
    print("Testing DICOM Viewer Image Quality Fixes...")
    print("=" * 50)
    
    js_file = "static/js/dicom_viewer.js"
    
    if not os.path.exists(js_file):
        print(f"ERROR: {js_file} not found!")
        return False
    
    with open(js_file, 'r') as f:
        content = f.read()
    
    tests = [
        ("high_quality: 'true'", "High quality mode enabled"),
        ("density_enhancement: 'true'", "Density enhancement enabled"),
        ("contrast_optimization: 'medical'", "Medical contrast optimization enabled"),
        ("this.windowWidth = 1500", "Window width optimized for lung imaging"),
        ("this.windowLevel = -600", "Window level optimized for lung imaging"),
        ("this.densityMultiplier = 1.3", "Density multiplier enhanced"),
        ("this.contrastBoostMultiplier = 1.25", "Contrast boost enhanced"),
        ("this.highQualityMode = true", "High quality mode flag enabled")
    ]
    
    all_passed = True
    for test_string, description in tests:
        if test_string in content:
            print(f"✅ {description}")
        else:
            print(f"❌ {description}")
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    if test_javascript_fixes():
        print("\n🎉 ALL FIXES APPLIED SUCCESSFULLY!")
        print("Images should now display with high quality like Image 1")
    else:
        print("\n❌ Some fixes missing!")
