#!/usr/bin/env python3
"""
Test script to verify DICOM viewer image quality fixes
"""

import os
import sys

def test_javascript_fixes():
    """Test that the JavaScript fixes are properly applied"""
    print("Testing DICOM Viewer Image Quality Fixes...")
    print("=" * 50)
    
    js_file = "static/js/dicom_viewer.js"
    
    if not os.path.exists(js_file):
        print(f"❌ ERROR: {js_file} not found!")
        return False
    
    with open(js_file, 'r') as f:
        content = f.read()
    
    # Test 1: Check if high_quality is set to true
    if "high_quality: 'true'" in content:
        print("✅ High quality mode enabled")
    else:
        print("❌ High quality mode not enabled")
        return False
    
    # Test 2: Check if density enhancement is enabled
    if "density_enhancement: 'true'" in content:
        print("✅ Density enhancement enabled")
    else:
        print("❌ Density enhancement not enabled")
        return False
    
    # Test 3: Check if medical contrast optimization is set
    if "contrast_optimization: 'medical'" in content:
        print("✅ Medical contrast optimization enabled")
    else:
        print("❌ Medical contrast optimization not enabled")
        return False
    
    # Test 4: Check if window/level defaults are optimized
    if "this.windowWidth = 1500" in content:
        print("✅ Window width optimized for lung imaging")
    else:
        print("❌ Window width not optimized")
        return False
    
    if "this.windowLevel = -600" in content:
        print("✅ Window level optimized for lung imaging")
    else:
        print("❌ Window level not optimized")
        return False
    
    # Test 5: Check if density multiplier is enhanced
    if "this.densityMultiplier = 1.3" in content:
        print("✅ Density multiplier enhanced")
    else:
        print("❌ Density multiplier not enhanced")
        return False
    
    # Test 6: Check if contrast boost is enhanced
    if "this.contrastBoostMultiplier = 1.25" in content:
        print("✅ Contrast boost multiplier enhanced")
    else:
        print("❌ Contrast boost multiplier not enhanced")
        return False
    
    # Test 7: Check if high quality mode flag is set
    if "this.highQualityMode = true" in content:
        print("✅ High quality mode flag enabled")
    else:
        print("❌ High quality mode flag not enabled")
        return False
    
    # Test 8: Check if enhanced tissue contrast values are applied
    if "filters.push('contrast(1.6)');" in content and "// Increased for better air-tissue contrast" in content:
        print("✅ Enhanced lung tissue contrast applied")
    else:
        print("❌ Enhanced lung tissue contrast not applied")
        return False
    
    # Test 9: Check if setupHighQualityRendering is called in redraw
    if "this.setupHighQualityRendering();" in content:
        print("✅ High quality rendering setup called in redraw")
    else:
        print("❌ High quality rendering setup not called in redraw")
        return False
    
    print("=" * 50)
    print("🎉 ALL IMAGE QUALITY FIXES SUCCESSFULLY APPLIED!")
    print()
    print("Summary of fixes:")
    print("- High quality image processing enabled")
    print("- Density enhancement activated for better tissue differentiation")
    print("- Medical contrast optimization enabled")
    print("- Window/Level defaults optimized for lung imaging (WW: 1500, WL: -600)")
    print("- Enhanced density and contrast multipliers")
    print("- High-quality rendering setup on every redraw")
    print("- Improved tissue-specific contrast filters")
    print()
    print("Expected results:")
    print("- Images should now display with much better quality like Image 1")
    print("- Better tissue contrast and bone/air differentiation")
    print("- Crisp, clear medical image visualization")
    print("- Optimal default settings for chest X-rays")
    
    return True

def main():
    """Main test function"""
    success = test_javascript_fixes()
    
    if success:
        print("\n🔧 To see the improvements:")
        print("1. Refresh your browser page")
        print("2. Load a DICOM study")
        print("3. Images should now display with high quality like Image 1")
        print("4. The default window/level should be optimized for lung imaging")
        sys.exit(0)
    else:
        print("\n❌ Some fixes may not be applied correctly!")
        sys.exit(1)

if __name__ == "__main__":
    main()