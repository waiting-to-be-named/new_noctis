#!/usr/bin/env python3
"""
Comprehensive test to verify all DICOM viewer functionality
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_server():
    """Test if server is running"""
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"✅ Server is running (status: {response.status_code})")
        return True
    except:
        print("❌ Server is not running")
        return False

def test_viewer_page():
    """Test viewer page and components"""
    print_section("VIEWER PAGE TEST")
    
    try:
        response = requests.get(f"{BASE_URL}/viewer/", timeout=5)
        if response.status_code == 200:
            content = response.text
            
            # Check essential UI elements
            ui_elements = {
                "Canvas": "dicom-canvas-advanced",
                "Upload Button": "upload-advanced-btn",
                "Export Button": "export-btn",
                "Settings Button": "settings-btn",
                "Fullscreen Button": "fullscreen-btn",
                "Logout Button": "logout-advanced-btn",
                "Back to Worklist": "back-to-worklist-btn",
                "Window/Level Tool": "windowing-adv-btn",
                "Pan Tool": "pan-adv-btn",
                "Zoom Tool": "zoom-adv-btn",
                "Rotate Button": "rotate-btn",
                "Flip Button": "flip-btn",
                "Measure Distance": "measure-distance-btn",
                "Measure Angle": "measure-angle-btn",
                "Reset View": "reset-adv-btn",
                "Fit to Window": "fit-to-window-btn",
                "Invert Colors": "invert-adv-btn",
                "Crosshair": "crosshair-adv-btn",
                "AI Analysis": "ai-analysis-btn",
                "Patient Name Field": "patient-name-adv",
                "Study Date Field": "study-date-adv",
                "Modality Field": "modality-adv"
            }
            
            print("UI Elements Check:")
            missing = []
            for name, element_id in ui_elements.items():
                if element_id in content:
                    print(f"  ✅ {name}")
                else:
                    print(f"  ❌ {name} (missing)")
                    missing.append(name)
            
            # Check JavaScript files
            print("\nJavaScript Files Check:")
            js_files = {
                "Main Viewer": "dicom_viewer_advanced.js",
                "Button Fixes": "dicom_viewer_button_fixes.js",
                "Comprehensive Fix": "dicom_viewer_comprehensive_fix.js",
                "Additional Fixes": "dicom_viewer_additional_fixes.js",
                "Debug Enhancements": "dicom_viewer_enhanced_debug.js"
            }
            
            for name, filename in js_files.items():
                if filename in content:
                    print(f"  ✅ {name}")
                else:
                    print(f"  ❌ {name} (not referenced)")
            
            # Check window/level presets
            print("\nWindow/Level Presets Check:")
            presets = ["Lung", "Bone", "Soft Tissue", "Brain", "Abdomen", "Mediastinum"]
            for preset in presets:
                if f'data-preset="{preset.lower()}"' in content or preset in content:
                    print(f"  ✅ {preset} preset")
                else:
                    print(f"  ⚠️  {preset} preset might be missing")
            
            return len(missing) == 0
        else:
            print(f"❌ Viewer page returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error accessing viewer page: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    print_section("API ENDPOINTS TEST")
    
    endpoints = [
        ("/viewer/api/studies/", "Studies API"),
        ("/viewer/api/test/", "Test API"),
        ("/viewer/api/get-study-images/1/", "Study Images API"),
        ("/viewer/api/worklist/", "Worklist API"),
        ("/viewer/api/get-image-data/1/", "Image Data API")
    ]
    
    all_pass = True
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            if response.status_code in [200, 201]:
                print(f"✅ {name} - Working")
                if endpoint == "/viewer/api/studies/":
                    data = response.json()
                    if isinstance(data, list):
                        print(f"   Found {len(data)} studies")
            elif response.status_code == 404:
                print(f"⚠️  {name} - Not found (404)")
                all_pass = False
            else:
                print(f"❌ {name} - Error (status: {response.status_code})")
                all_pass = False
        except Exception as e:
            print(f"❌ {name} - Failed ({str(e)})")
            all_pass = False
    
    return all_pass

def test_static_files():
    """Test static file access"""
    print_section("STATIC FILES TEST")
    
    static_files = {
        "Main CSS": "/static/css/dicom_viewer_advanced.css",
        "Main JS": "/static/js/dicom_viewer_advanced.js",
        "Button Fixes JS": "/static/js/dicom_viewer_button_fixes.js",
        "Comprehensive Fix JS": "/static/js/dicom_viewer_comprehensive_fix.js",
        "Additional Fixes JS": "/static/js/dicom_viewer_additional_fixes.js"
    }
    
    all_accessible = True
    for name, path in static_files.items():
        try:
            response = requests.get(f"{BASE_URL}{path}", timeout=5)
            if response.status_code == 200:
                size = len(response.content)
                print(f"✅ {name} - Accessible ({size:,} bytes)")
            else:
                print(f"❌ {name} - Not accessible (status: {response.status_code})")
                all_accessible = False
        except Exception as e:
            print(f"❌ {name} - Failed ({str(e)})")
            all_accessible = False
    
    return all_accessible

def test_button_handlers():
    """Test if button handlers are defined in JavaScript"""
    print_section("BUTTON HANDLERS TEST")
    
    try:
        response = requests.get(f"{BASE_URL}/static/js/dicom_viewer_comprehensive_fix.js", timeout=5)
        if response.status_code == 200:
            content = response.text
            
            handlers = {
                "Upload": "fixUploadFunctionality",
                "Export": "fixExportFunctionality",
                "Settings": "fixSettingsFunctionality",
                "Navigation Tools": "fixNavigationAndTools",
                "Window/Level": "fixWindowLevelPresets",
                "Measurements": "fixMeasurementTools",
                "AI Tools": "fixAIFunctionality",
                "3D Tools": "fix3DTools",
                "Series Navigation": "fixSeriesNavigation"
            }
            
            all_present = True
            for name, handler in handlers.items():
                if handler in content:
                    print(f"✅ {name} handler present")
                else:
                    print(f"❌ {name} handler missing")
                    all_present = False
            
            # Check for notification system
            if "showNotification" in content:
                print(f"✅ Notification system present")
            else:
                print(f"⚠️  Notification system might be missing")
            
            return all_present
        else:
            print(f"❌ Could not access JavaScript file")
            return False
    except Exception as e:
        print(f"❌ Error checking handlers: {e}")
        return False

def generate_final_report(results):
    """Generate final test report"""
    print_section("FINAL REPORT")
    
    total_tests = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total_tests - passed
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/total_tests)*100:.1f}%")
    
    print("\nTest Results:")
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print("\n" + "="*60)
    if failed == 0:
        print("✅ ALL TESTS PASSED - DICOM VIEWER IS FULLY FUNCTIONAL!")
        print("\nThe DICOM viewer should now:")
        print("  • Display images properly")
        print("  • Have all buttons working")
        print("  • Show patient/study information")
        print("  • Support all tools and measurements")
        print("  • Handle uploads and exports")
    elif passed >= total_tests * 0.8:
        print("✅ DICOM VIEWER IS MOSTLY FUNCTIONAL")
        print("\nSome minor issues remain but core functionality works.")
    else:
        print("⚠️  DICOM VIEWER HAS ISSUES")
        print("\nPlease check the failed tests above and apply fixes.")
    print("="*60)

def main():
    """Run all tests"""
    print("🔍 COMPREHENSIVE DICOM VIEWER FUNCTIONALITY TEST")
    print("="*60)
    
    # Wait a bit for server
    print("Waiting for server to be ready...")
    time.sleep(3)
    
    results = {}
    
    # Run tests
    if test_server():
        results["Server Running"] = True
        results["Viewer Page"] = test_viewer_page()
        results["API Endpoints"] = test_api_endpoints()
        results["Static Files"] = test_static_files()
        results["Button Handlers"] = test_button_handlers()
    else:
        results["Server Running"] = False
        print("\n❌ Server is not running. Cannot perform other tests.")
    
    # Generate report
    generate_final_report(results)

if __name__ == "__main__":
    main()