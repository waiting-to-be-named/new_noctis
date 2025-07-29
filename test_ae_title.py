#!/usr/bin/env python3
"""
Test script for AE title generation functionality
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/workspace')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from viewer.models import Facility

def test_ae_title_generation():
    """Test the AE title generation functionality"""
    print("Testing AE title generation...")
    
    # Test 1: Basic facility name
    facility1 = Facility(name="General Hospital")
    facility1.save()
    print(f"Facility: {facility1.name} -> AE Title: {facility1.ae_title}")
    
    # Test 2: Facility with special characters
    facility2 = Facility(name="St. Mary's Medical Center")
    facility2.save()
    print(f"Facility: {facility2.name} -> AE Title: {facility2.ae_title}")
    
    # Test 3: Short facility name
    facility3 = Facility(name="ABC")
    facility3.save()
    print(f"Facility: {facility3.name} -> AE Title: {facility3.ae_title}")
    
    # Test 4: Very long facility name
    facility4 = Facility(name="University of California San Francisco Medical Center")
    facility4.save()
    print(f"Facility: {facility4.name} -> AE Title: {facility4.ae_title}")
    
    # Test 5: Duplicate name (should generate different AE title)
    facility5 = Facility(name="General Hospital")
    facility5.save()
    print(f"Facility: {facility5.name} -> AE Title: {facility5.ae_title}")
    
    # Test 6: Manual AE title
    facility6 = Facility(name="Test Hospital", ae_title="TESTHOSP")
    facility6.save()
    print(f"Facility: {facility6.name} -> AE Title: {facility6.ae_title}")
    
    print("\nAE title generation test completed!")
    
    # Clean up test data
    for facility in [facility1, facility2, facility3, facility4, facility5, facility6]:
        facility.delete()
    
    print("Test data cleaned up.")

if __name__ == "__main__":
    test_ae_title_generation()