#!/usr/bin/env python3
"""
Test script to verify DICOM viewer functionality
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_viewer_endpoints():
    """Test the DICOM viewer API endpoints"""
    
    print("Testing DICOM Viewer API Endpoints...")
    
    # Test studies endpoint
    try:
        response = requests.get(f"{BASE_URL}/viewer/api/studies/")
        print(f"Studies endpoint status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data)} studies")
            if data:
                study_id = data[0]['id']
                print(f"Testing with study ID: {study_id}")
                
                # Test series endpoint
                series_response = requests.get(f"{BASE_URL}/viewer/api/studies/{study_id}/series/")
                print(f"Series endpoint status: {series_response.status_code}")
                if series_response.status_code == 200:
                    series_data = series_response.json()
                    print(f"Found {len(series_data.get('series', []))} series")
                    
                    if series_data.get('series'):
                        series_id = series_data['series'][0]['id']
                        print(f"Testing with series ID: {series_id}")
                        
                        # Test images endpoint
                        images_response = requests.get(f"{BASE_URL}/viewer/api/series/{series_id}/images/")
                        print(f"Images endpoint status: {images_response.status_code}")
                        if images_response.status_code == 200:
                            images_data = images_response.json()
                            print(f"Found {len(images_data.get('images', []))} images")
                            
                            if images_data.get('images'):
                                image_id = images_data['images'][0]['id']
                                print(f"Testing with image ID: {image_id}")
                                
                                # Test image data endpoint
                                image_data_response = requests.get(f"{BASE_URL}/viewer/api/images/{image_id}/data/")
                                print(f"Image data endpoint status: {image_data_response.status_code}")
                                if image_data_response.status_code == 200:
                                    image_data = image_data_response.json()
                                    has_image_data = 'image_data' in image_data
                                    has_metadata = 'metadata' in image_data
                                    print(f"Image data contains image_data: {has_image_data}")
                                    print(f"Image data contains metadata: {has_metadata}")
                                    
                                    if has_image_data:
                                        image_data_str = image_data['image_data']
                                        is_base64 = image_data_str.startswith('data:image/')
                                        print(f"Image data is base64 format: {is_base64}")
                                        print(f"Image data length: {len(image_data_str)} characters")
                                        
                                        print("✅ All endpoints working correctly!")
                                        return True
                                else:
                                    print(f"❌ Image data endpoint failed: {image_data_response.text}")
                            else:
                                print("❌ No images found in series")
                        else:
                            print(f"❌ Images endpoint failed: {images_response.text}")
                    else:
                        print("❌ No series found in study")
                else:
                    print(f"❌ Series endpoint failed: {series_response.text}")
            else:
                print("❌ No studies found")
        else:
            print(f"❌ Studies endpoint failed: {response.text}")
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")
    
    return False

def test_viewer_page():
    """Test if the viewer page loads correctly"""
    try:
        response = requests.get(f"{BASE_URL}/viewer/")
        print(f"Viewer page status: {response.status_code}")
        if response.status_code == 200:
            content = response.text
            has_canvas = 'dicom-canvas-advanced' in content
            has_back_button = 'back-to-worklist-btn' in content
            has_advanced_js = 'dicom_viewer_advanced.js' in content
            
            print(f"Page contains DICOM canvas: {has_canvas}")
            print(f"Page contains back to worklist button: {has_back_button}")
            print(f"Page loads advanced JS: {has_advanced_js}")
            
            if has_canvas and has_back_button and has_advanced_js:
                print("✅ Viewer page loads correctly!")
                return True
            else:
                print("❌ Viewer page missing some components")
        else:
            print(f"❌ Viewer page failed to load: {response.text}")
    except Exception as e:
        print(f"❌ Error testing viewer page: {e}")
    
    return False

if __name__ == "__main__":
    print("DICOM Viewer Functionality Test")
    print("=" * 40)
    
    # Test viewer page
    page_ok = test_viewer_page()
    print()
    
    # Test API endpoints
    api_ok = test_viewer_endpoints()
    print()
    
    if page_ok and api_ok:
        print("🎉 All tests passed! DICOM viewer should be working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")