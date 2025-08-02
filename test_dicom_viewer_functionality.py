#!/usr/bin/env python3
"""
Test script to verify DICOM viewer functionality
"""

import time
import requests
import json
from pathlib import Path

# Base URL for the application
BASE_URL = "http://localhost:8000"

# Test results storage
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def test_server_running():
    """Test if the server is running"""
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code == 200:
            test_results["passed"].append("Server is running")
            return True
        else:
            test_results["failed"].append(f"Server returned status code: {response.status_code}")
            return False
    except Exception as e:
        test_results["failed"].append(f"Server not accessible: {str(e)}")
        return False

def test_viewer_page():
    """Test if the viewer page loads"""
    try:
        response = requests.get(f"{BASE_URL}/viewer/", timeout=5)
        if response.status_code == 200:
            # Check for essential elements
            content = response.text
            essential_elements = [
                'dicom-canvas-advanced',
                'upload-advanced-btn',
                'export-btn',
                'settings-btn',
                'windowing-adv-btn',
                'pan-adv-btn',
                'zoom-adv-btn',
                'measure-distance-btn',
                'reset-adv-btn'
            ]
            
            missing_elements = []
            for element in essential_elements:
                if element not in content:
                    missing_elements.append(element)
            
            if missing_elements:
                test_results["warnings"].append(f"Missing elements in viewer page: {', '.join(missing_elements)}")
            else:
                test_results["passed"].append("All essential viewer elements present")
            
            # Check for JavaScript files
            js_files = [
                'dicom_viewer_comprehensive_fix.js',
                'dicom_viewer_advanced.js'
            ]
            
            missing_js = []
            for js_file in js_files:
                if js_file not in content:
                    missing_js.append(js_file)
            
            if missing_js:
                test_results["warnings"].append(f"Missing JavaScript files: {', '.join(missing_js)}")
            else:
                test_results["passed"].append("All JavaScript files referenced")
            
            return True
        else:
            test_results["failed"].append(f"Viewer page returned status code: {response.status_code}")
            return False
    except Exception as e:
        test_results["failed"].append(f"Viewer page not accessible: {str(e)}")
        return False

def test_static_files():
    """Test if static files are served correctly"""
    static_files = [
        "/static/js/dicom_viewer_comprehensive_fix.js",
        "/static/js/dicom_viewer_advanced.js",
        "/static/css/dicom_viewer_advanced.css"
    ]
    
    for file_path in static_files:
        try:
            response = requests.get(f"{BASE_URL}{file_path}", timeout=5)
            if response.status_code == 200:
                test_results["passed"].append(f"Static file accessible: {file_path}")
            else:
                test_results["failed"].append(f"Static file not found: {file_path} (status: {response.status_code})")
        except Exception as e:
            test_results["failed"].append(f"Error accessing static file {file_path}: {str(e)}")

def test_api_endpoints():
    """Test API endpoints"""
    endpoints = [
        ("/viewer/api/studies/", "GET"),
        ("/viewer/api/series/", "GET"),
        ("/viewer/api/viewer-state/", "GET")
    ]
    
    for endpoint, method in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            
            if response.status_code in [200, 201]:
                test_results["passed"].append(f"API endpoint accessible: {endpoint}")
            elif response.status_code == 404:
                test_results["warnings"].append(f"API endpoint not found: {endpoint}")
            else:
                test_results["warnings"].append(f"API endpoint returned status {response.status_code}: {endpoint}")
        except Exception as e:
            test_results["failed"].append(f"Error accessing API endpoint {endpoint}: {str(e)}")

def check_button_functionality():
    """Check if buttons have proper handlers"""
    # This would require Selenium or similar for full testing
    # For now, we just check if the JavaScript files that handle buttons are loaded
    try:
        response = requests.get(f"{BASE_URL}/static/js/dicom_viewer_comprehensive_fix.js", timeout=5)
        if response.status_code == 200:
            content = response.text
            button_handlers = [
                "fixUploadFunctionality",
                "fixExportFunctionality", 
                "fixSettingsFunctionality",
                "fixNavigationAndTools",
                "fixWindowLevelPresets",
                "fixMeasurementTools"
            ]
            
            missing_handlers = []
            for handler in button_handlers:
                if handler not in content:
                    missing_handlers.append(handler)
            
            if missing_handlers:
                test_results["warnings"].append(f"Missing button handlers: {', '.join(missing_handlers)}")
            else:
                test_results["passed"].append("All button handler functions present")
    except Exception as e:
        test_results["failed"].append(f"Could not check button functionality: {str(e)}")

def generate_report():
    """Generate test report"""
    print("\n" + "="*60)
    print("DICOM VIEWER FUNCTIONALITY TEST REPORT")
    print("="*60)
    
    print(f"\n✅ PASSED TESTS ({len(test_results['passed'])})")
    print("-"*40)
    for test in test_results["passed"]:
        print(f"  ✓ {test}")
    
    print(f"\n⚠️  WARNINGS ({len(test_results['warnings'])})")
    print("-"*40)
    for warning in test_results["warnings"]:
        print(f"  ⚠ {warning}")
    
    print(f"\n❌ FAILED TESTS ({len(test_results['failed'])})")
    print("-"*40)
    for test in test_results["failed"]:
        print(f"  ✗ {test}")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("-"*40)
    total_tests = len(test_results["passed"]) + len(test_results["failed"]) + len(test_results["warnings"])
    print(f"Total tests: {total_tests}")
    print(f"Passed: {len(test_results['passed'])}")
    print(f"Warnings: {len(test_results['warnings'])}")
    print(f"Failed: {len(test_results['failed'])}")
    
    if test_results["failed"]:
        print("\n⚠️  CRITICAL ISSUES FOUND - DICOM VIEWER MAY NOT FUNCTION PROPERLY")
    elif test_results["warnings"]:
        print("\n⚠️  SOME ISSUES FOUND - DICOM VIEWER MAY HAVE LIMITED FUNCTIONALITY")
    else:
        print("\n✅ ALL TESTS PASSED - DICOM VIEWER SHOULD BE FULLY FUNCTIONAL")

def main():
    """Run all tests"""
    print("Starting DICOM Viewer functionality tests...")
    print("Waiting for server to start...")
    time.sleep(5)
    
    # Run tests
    if test_server_running():
        test_viewer_page()
        test_static_files()
        test_api_endpoints()
        check_button_functionality()
    
    # Generate report
    generate_report()

if __name__ == "__main__":
    main()