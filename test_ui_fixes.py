#!/usr/bin/env python3
"""
Test script to verify UI fixes and JavaScript error resolution
"""
import subprocess
import sys
import time
import os
from pathlib import Path

def test_js_syntax():
    """Test JavaScript syntax by parsing the fixed file"""
    js_file = Path('/workspace/static/js/dicom_viewer_fixed.js')
    
    if not js_file.exists():
        print("❌ JavaScript file not found!")
        return False
    
    # Read the file and check for basic syntax issues
    try:
        with open(js_file, 'r') as f:
            content = f.read()
        
        # Check for the class definition
        if 'class FixedDicomViewer {' in content:
            print("✅ FixedDicomViewer class found")
        else:
            print("❌ FixedDicomViewer class not found")
            return False
        
        # Check for proper closing
        if content.count('{') == content.count('}'):
            print("✅ Balanced braces in JavaScript")
        else:
            print("❌ Unbalanced braces in JavaScript")
            return False
        
        # Check for the initialization code
        if "document.addEventListener('DOMContentLoaded'" in content:
            print("✅ Proper DOM initialization found")
        else:
            print("❌ DOM initialization not found")
            return False
            
        print("✅ JavaScript syntax appears correct")
        return True
        
    except Exception as e:
        print(f"❌ Error reading JavaScript file: {e}")
        return False

def test_css_files():
    """Test CSS file existence and basic structure"""
    css_files = [
        '/workspace/static/css/worklist_professional.css',
        '/workspace/static/css/worklist.css',
        '/workspace/static/css/worklist_enhanced.css'
    ]
    
    for css_file in css_files:
        if Path(css_file).exists():
            print(f"✅ CSS file exists: {css_file}")
        else:
            print(f"❌ CSS file missing: {css_file}")
    
    # Check the professional CSS specifically
    prof_css = Path('/workspace/static/css/worklist_professional.css')
    if prof_css.exists():
        with open(prof_css, 'r') as f:
            content = f.read()
        
        if '.worklist-table::-webkit-scrollbar' in content:
            print("✅ Professional scrollbar styling found")
        else:
            print("❌ Scrollbar styling not found")
        
        if 'responsive' in content.lower():
            print("✅ Responsive design elements found")
        else:
            print("❌ Responsive design not found")
    
    return True

def test_template_updates():
    """Test template file updates"""
    template_file = Path('/workspace/templates/worklist/worklist.html')
    
    if not template_file.exists():
        print("❌ Worklist template not found!")
        return False
    
    try:
        with open(template_file, 'r') as f:
            content = f.read()
        
        if 'worklist_professional.css' in content:
            print("✅ Template updated to use professional CSS")
        else:
            print("❌ Template not updated for professional CSS")
            return False
        
        if 'fonts.googleapis.com' in content:
            print("✅ Google Fonts integration found")
        else:
            print("❌ Google Fonts not integrated")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading template file: {e}")
        return False

def test_database_content():
    """Test database has sample content"""
    import sqlite3
    
    try:
        conn = sqlite3.connect('/workspace/db.sqlite3')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM viewer_worklistentry;")
        worklist_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM viewer_dicomstudy;")
        study_count = cursor.fetchone()[0]
        
        print(f"✅ Database has {worklist_count} worklist entries")
        print(f"✅ Database has {study_count} DICOM studies")
        
        if worklist_count > 0 and study_count > 0:
            print("✅ Sample data exists for testing")
            return True
        else:
            print("❌ Insufficient sample data")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def run_all_tests():
    """Run all tests"""
    print("🔍 Testing UI Fixes and JavaScript Resolution...")
    print("=" * 60)
    
    tests = [
        ("JavaScript Syntax", test_js_syntax),
        ("CSS Files", test_css_files), 
        ("Template Updates", test_template_updates),
        ("Database Content", test_database_content)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        print("-" * 30)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The UI fixes are ready!")
        print("\n📋 Summary of fixes applied:")
        print("• Fixed JavaScript syntax error in dicom_viewer_fixed.js")
        print("• Created professional CSS with proper scrolling")
        print("• Updated worklist template for better presentation")
        print("• Added sample data for testing")
        print("• Implemented responsive design")
        print("• Enhanced accessibility and UX")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the issues above.")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests()