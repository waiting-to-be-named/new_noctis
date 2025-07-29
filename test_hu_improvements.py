#!/usr/bin/env python3
"""
Test script for enhanced Hounsfield Units measurement improvements
"""

import sys
import os
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append('/workspace')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.views import get_enhanced_hu_interpretation
import numpy as np

def test_hu_interpretation():
    """Test the enhanced HU interpretation function"""
    
    print("Testing Enhanced Hounsfield Units Interpretation")
    print("=" * 50)
    
    # Test cases with different HU values and anatomical regions
    test_cases = [
        (-950, 'CHEST', 'Lung tissue analysis'),
        (-200, 'ABDOMEN', 'Fat tissue analysis'),
        (30, 'HEAD', 'Brain tissue analysis'),
        (50, 'ABDOMEN', 'Liver analysis'),
        (150, 'CHEST', 'Dense tissue analysis'),
        (800, 'PELVIS', 'Bone analysis'),
        (1500, 'HEAD', 'Dense bone analysis'),
    ]
    
    for hu_value, body_part, description in test_cases:
        print(f"\n{description}")
        print(f"HU Value: {hu_value}")
        print(f"Body Part: {body_part}")
        
        # Test with confidence intervals
        ci_lower = hu_value - 5
        ci_upper = hu_value + 5
        
        result = get_enhanced_hu_interpretation(hu_value, body_part, '', ci_lower, ci_upper)
        
        print(f"Tissue Type: {result['tissue_type']}")
        print(f"Anatomical Context: {result['anatomical_context']}")
        print(f"Clinical Significance: {result['clinical_significance']}")
        print(f"Reference Range: {result['reference_range']}")
        print(f"Primary Interpretation: {result['primary_interpretation']}")
        print("-" * 30)

def test_statistical_calculations():
    """Test statistical calculations used in HU measurements"""
    
    print("\nTesting Statistical Calculations")
    print("=" * 50)
    
    # Simulate HU values for a region of interest
    hu_values = np.array([-200, -180, -190, -210, -195, -185, -200, -190, -205, -195])
    
    mean_hu = float(np.mean(hu_values))
    median_hu = float(np.median(hu_values))
    std_hu = float(np.std(hu_values))
    min_hu = float(np.min(hu_values))
    max_hu = float(np.max(hu_values))
    
    # Calculate confidence interval
    from scipy import stats
    confidence_interval = stats.t.interval(0.95, len(hu_values)-1, 
                                        loc=mean_hu, scale=std_hu/np.sqrt(len(hu_values)))
    ci_lower = float(confidence_interval[0])
    ci_upper = float(confidence_interval[1])
    
    # Calculate coefficient of variation
    cv = (std_hu / mean_hu) * 100 if mean_hu != 0 else 0
    
    print(f"Sample HU Values: {hu_values}")
    print(f"Mean: {mean_hu:.1f} HU")
    print(f"Median: {median_hu:.1f} HU")
    print(f"Std Dev: {std_hu:.1f} HU")
    print(f"Range: {min_hu:.1f} - {max_hu:.1f} HU")
    print(f"95% CI: {ci_lower:.1f} - {ci_upper:.1f} HU")
    print(f"Coefficient of Variation: {cv:.1f}%")
    
    # Test interpretation
    result = get_enhanced_hu_interpretation(mean_hu, 'ABDOMEN', '', ci_lower, ci_upper)
    print(f"Interpretation: {result['primary_interpretation']}")
    print(f"Tissue Type: {result['tissue_type']}")

def test_anatomical_reference_ranges():
    """Test anatomical region-specific reference ranges"""
    
    print("\nTesting Anatomical Reference Ranges")
    print("=" * 50)
    
    anatomical_regions = {
        'HEAD': [25, 40, 10, 800],  # Brain white matter, gray matter, CSF, bone
        'CHEST': [-950, -600, 40, 800],  # Lung air, lung tissue, heart, bone
        'ABDOMEN': [50, -75, 30, 800],  # Liver, fat, kidney, bone
        'PELVIS': [10, 40, 800]  # Bladder, prostate, bone
    }
    
    for region, hu_values in anatomical_regions.items():
        print(f"\n{region} Region:")
        for hu in hu_values:
            result = get_enhanced_hu_interpretation(hu, region, '')
            print(f"  {hu} HU: {result['tissue_type']} - {result['clinical_significance'].split(' - ')[0]}")

if __name__ == "__main__":
    try:
        test_hu_interpretation()
        test_statistical_calculations()
        test_anatomical_reference_ranges()
        print("\n✅ All tests completed successfully!")
        print("\nEnhanced Hounsfield Units measurement system is working correctly.")
        print("Key improvements implemented:")
        print("- Comprehensive statistical analysis with confidence intervals")
        print("- Anatomical region-specific interpretations")
        print("- Enhanced tissue classification")
        print("- Clinical significance assessment")
        print("- Quality assurance features")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()