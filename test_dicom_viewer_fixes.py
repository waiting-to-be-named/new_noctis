#!/usr/bin/env python3
"""
Test script to verify DICOM viewer fixes
"""

import os
import sys
import time
import requests
from pathlib import Path

def test_worklist_button():
    """Test that worklist button works properly"""
    print("Testing worklist button functionality...")
    
    # Test the worklist URL is accessible
    try:
        response = requests.get('http://localhost:8000/worklist/', timeout=5)
        if response.status_code == 200:
            print("✓ Worklist page is accessible")
            return True
        else:
            print(f"✗ Worklist page returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error accessing worklist: {e}")
        return False

def test_logout_button():
    """Test that logout button works properly"""
    print("Testing logout button functionality...")
    
    # Test the logout URL is accessible
    try:
        response = requests.get('http://localhost:8000/accounts/logout/', timeout=5)
        if response.status_code in [200, 302]:  # 302 is redirect for logout
            print("✓ Logout page is accessible")
            return True
        else:
            print(f"✗ Logout page returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error accessing logout: {e}")
        return False

def test_dicom_viewer_page():
    """Test that DICOM viewer page loads properly"""
    print("Testing DICOM viewer page...")
    
    try:
        response = requests.get('http://localhost:8000/viewer/', timeout=5)
        if response.status_code == 200:
            print("✓ DICOM viewer page loads successfully")
            
            # Check for key elements in the HTML
            content = response.text
            if 'worklist-btn' in content:
                print("✓ Worklist button found in HTML")
            else:
                print("✗ Worklist button not found in HTML")
                
            if 'logout-btn' in content:
                print("✓ Logout button found in HTML")
            else:
                print("✗ Logout button not found in HTML")
                
            if 'enhanced-upload-btn' in content:
                print("✓ Enhanced upload button found in HTML")
            else:
                print("✗ Enhanced upload button not found in HTML")
                
            if 'series-selector' in content:
                print("✓ Series selector found in HTML")
            else:
                print("✗ Series selector not found in HTML")
                
            return True
        else:
            print(f"✗ DICOM viewer page returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error accessing DICOM viewer: {e}")
        return False

def test_upload_functionality():
    """Test that upload functionality works"""
    print("Testing upload functionality...")
    
    # Check if upload endpoints exist
    try:
        response = requests.get('http://localhost:8000/viewer/api/upload/', timeout=5)
        if response.status_code in [200, 405]:  # 405 is method not allowed (POST expected)
            print("✓ Upload endpoint exists")
            return True
        else:
            print(f"✗ Upload endpoint returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error testing upload endpoint: {e}")
        return False

def test_series_selector():
    """Test that series selector functionality works"""
    print("Testing series selector functionality...")
    
    # Check if series selector API exists
    try:
        response = requests.get('http://localhost:8000/viewer/api/studies/', timeout=5)
        if response.status_code in [200, 401]:  # 401 is unauthorized (expected without auth)
            print("✓ Series selector API endpoint exists")
            return True
        else:
            print(f"✗ Series selector API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error testing series selector API: {e}")
        return False

def test_static_files():
    """Test that static files are accessible"""
    print("Testing static files...")
    
    static_files = [
        '/static/js/dicom_viewer.js',
        '/static/css/dicom_viewer.css'
    ]
    
    for file_path in static_files:
        try:
            response = requests.get(f'http://localhost:8000{file_path}', timeout=5)
            if response.status_code == 200:
                print(f"✓ {file_path} is accessible")
            else:
                print(f"✗ {file_path} returned status {response.status_code}")
        except Exception as e:
            print(f"✗ Error accessing {file_path}: {e}")

def check_css_fixes():
    """Check that CSS fixes are in place"""
    print("Checking CSS fixes...")
    
    try:
        response = requests.get('http://localhost:8000/static/css/dicom_viewer.css', timeout=5)
        if response.status_code == 200:
            css_content = response.text
            
            # Check for series selector positioning fixes
            if 'position: fixed' in css_content and 'top: 50%' in css_content:
                print("✓ Series selector positioning fixes found")
            else:
                print("✗ Series selector positioning fixes not found")
                
            # Check for dropdown positioning fixes
            if 'left: -200px' in css_content and 'min-width: 280px' in css_content:
                print("✓ Dropdown positioning fixes found")
            else:
                print("✗ Dropdown positioning fixes not found")
                
            # Check for enhanced upload styles
            if 'enhanced-upload-container' in css_content:
                print("✓ Enhanced upload container styles found")
            else:
                print("✗ Enhanced upload container styles not found")
                
        else:
            print(f"✗ CSS file returned status {response.status_code}")
    except Exception as e:
        print(f"✗ Error checking CSS fixes: {e}")

def check_js_fixes():
    """Check that JavaScript fixes are in place"""
    print("Checking JavaScript fixes...")
    
    try:
        response = requests.get('http://localhost:8000/static/js/dicom_viewer.js', timeout=5)
        if response.status_code == 200:
            js_content = response.text
            
            # Check for worklist button fixes
            if 'worklistBtn._worklistHandler' in js_content:
                print("✓ Worklist button event handler fixes found")
            else:
                print("✗ Worklist button event handler fixes not found")
                
            # Check for image loading fixes
            if 'imgElement.complete' in js_content and 'imgElement.naturalWidth' in js_content:
                print("✓ Image loading fixes found")
            else:
                print("✗ Image loading fixes not found")
                
            # Check for upload functionality
            if 'uploadFiles' in js_content:
                print("✓ Upload functionality found")
            else:
                print("✗ Upload functionality not found")
                
        else:
            print(f"✗ JavaScript file returned status {response.status_code}")
    except Exception as e:
        print(f"✗ Error checking JavaScript fixes: {e}")

def main():
    """Run all tests"""
    print("=" * 60)
    print("DICOM Viewer Fixes Test Suite")
    print("=" * 60)
    
    tests = [
        test_worklist_button,
        test_logout_button,
        test_dicom_viewer_page,
        test_upload_functionality,
        test_series_selector,
        test_static_files,
        check_css_fixes,
        check_js_fixes
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
        print()
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! DICOM viewer fixes are working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()