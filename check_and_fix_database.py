#!/usr/bin/env python3
"""
Check and Fix Database Script
Checks if there are DICOM studies in the database and creates test data if needed
"""

import os
import sys
import sqlite3
import json
import base64
from datetime import datetime
import math
import random

def check_database():
    """Check the current state of the database"""
    print("🔍 Checking database state...")
    
    # Connect to SQLite database
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        
        # Check for studies
        cursor.execute("SELECT COUNT(*) FROM viewer_dicomstudy")
        study_count = cursor.fetchone()[0]
        
        # Check for series
        cursor.execute("SELECT COUNT(*) FROM viewer_dicomseries")
        series_count = cursor.fetchone()[0]
        
        # Check for images
        cursor.execute("SELECT COUNT(*) FROM viewer_dicomimage")
        image_count = cursor.fetchone()[0]
        
        print(f"📊 Database Status:")
        print(f"   Studies: {study_count}")
        print(f"   Series: {series_count}")
        print(f"   Images: {image_count}")
        
        if study_count > 0:
            # Get sample study info
            cursor.execute("""
                SELECT id, patient_name, patient_id, study_description, study_date 
                FROM viewer_dicomstudy 
                LIMIT 3
            """)
            studies = cursor.fetchall()
            print(f"\n📋 Sample Studies:")
            for study in studies:
                print(f"   ID: {study[0]}, Patient: {study[1]}, Description: {study[3]}")
        
        conn.close()
        return study_count, series_count, image_count
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return 0, 0, 0

def create_test_image():
    """Create a test medical image as base64 PNG"""
    # Create a simple PNG header and data for a 64x64 grayscale test image
    # This is a minimal PNG that can be used for testing
    width, height = 64, 64
    
    # Create a simple gradient pattern
    image_data = []
    for y in range(height):
        row = []
        for x in range(width):
            # Create a circular gradient pattern
            center_x, center_y = width // 2, height // 2
            distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
            max_distance = math.sqrt(center_x**2 + center_y**2)
            
            # Normalize distance and create gradient
            normalized = min(distance / max_distance, 1.0)
            pixel_value = int(255 * (1 - normalized))
            
            # Add some noise
            noise = random.randint(-20, 20)
            pixel_value = max(0, min(255, pixel_value + noise))
            
            row.append(pixel_value)
        image_data.append(row)
    
    # Create a simple PNG manually (base64 encoded)
    # For simplicity, we'll create a data URL with a basic pattern
    png_data = create_simple_png(image_data)
    return base64.b64encode(png_data).decode('utf-8')

def create_simple_png(image_data):
    """Create a minimal PNG from image data"""
    import struct
    import zlib
    
    width = len(image_data[0])
    height = len(image_data)
    
    # PNG signature
    png_signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0)
    ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
    ihdr_chunk = struct.pack('>I4s', len(ihdr_data), b'IHDR') + ihdr_data + struct.pack('>I', ihdr_crc)
    
    # IDAT chunk (image data)
    raw_data = b''
    for row in image_data:
        raw_data += b'\x00'  # Filter type 0 (None)
        for pixel in row:
            raw_data += struct.pack('B', pixel)
    
    compressed_data = zlib.compress(raw_data)
    idat_crc = zlib.crc32(b'IDAT' + compressed_data) & 0xffffffff
    idat_chunk = struct.pack('>I4s', len(compressed_data), b'IDAT') + compressed_data + struct.pack('>I', idat_crc)
    
    # IEND chunk
    iend_crc = zlib.crc32(b'IEND') & 0xffffffff
    iend_chunk = struct.pack('>I4s', 0, b'IEND') + struct.pack('>I', iend_crc)
    
    return png_signature + ihdr_chunk + idat_chunk + iend_chunk

def create_test_data():
    """Create test DICOM data in the database"""
    print("🔧 Creating test DICOM data...")
    
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        
        # Create a test study
        study_data = {
            'patient_name': 'TEST^PATIENT',
            'patient_id': 'TEST001',
            'study_description': 'CT Chest Test Study',
            'study_date': datetime.now().strftime('%Y-%m-%d'),
            'study_time': datetime.now().strftime('%H:%M:%S'),
            'study_instance_uid': 'TEST.STUDY.UID.001',
            'accession_number': 'ACC001',
            'referring_physician': 'Dr. Test',
            'modality': 'CT',
            'institution_name': 'Test Hospital'
        }
        
        cursor.execute("""
            INSERT INTO viewer_dicomstudy (
                patient_name, patient_id,
                study_description, study_date, study_time,
                study_instance_uid, accession_number, referring_physician,
                modality, institution_name, clinical_info, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            study_data['patient_name'], study_data['patient_id'],
            study_data['study_description'], study_data['study_date'], study_data['study_time'],
            study_data['study_instance_uid'], study_data['accession_number'], study_data['referring_physician'],
            study_data['modality'], study_data['institution_name'], 'Test clinical information',
            datetime.now().isoformat()
        ))
        
        study_id = cursor.lastrowid
        print(f"✅ Created test study with ID: {study_id}")
        
        # Create a test series
        series_data = {
            'series_instance_uid': 'TEST.SERIES.UID.001',
            'series_number': 1,
            'series_description': 'Axial CT Chest',
            'modality': 'CT',
            'body_part_examined': 'CHEST',
            'series_date': datetime.now().strftime('%Y-%m-%d'),
            'series_time': datetime.now().strftime('%H:%M:%S'),
            'protocol_name': 'Chest CT Protocol'
        }
        
        cursor.execute("""
            INSERT INTO viewer_dicomseries (
                study_id, series_instance_uid, series_number,
                series_description, modality, body_part_examined,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            study_id, series_data['series_instance_uid'], series_data['series_number'],
            series_data['series_description'], series_data['modality'], series_data['body_part_examined'],
            datetime.now().isoformat()
        ))
        
        series_id = cursor.lastrowid
        print(f"✅ Created test series with ID: {series_id}")
        
        # Create test images
        print("🖼️  Creating test images...")
        for i in range(3):
            # Create test image data as base64 PNG
            img_base64 = create_test_image()
            
            # Create a fake file path
            file_path = f'/test/image_{i+1}.dcm'
            
            image_data = {
                'sop_instance_uid': f'TEST.IMAGE.UID.{i+1:03d}',
                'instance_number': i + 1,
                'image_position_patient_x': 0.0,
                'image_position_patient_y': 0.0,
                'image_position_patient_z': float(i * 5),  # 5mm spacing
                'image_orientation_patient': '1\\0\\0\\0\\1\\0',
                'pixel_spacing_x': 0.5,
                'pixel_spacing_y': 0.5,
                'slice_thickness': 5.0,
                'rows': 64,
                'columns': 64,
                'bits_allocated': 8,
                'bits_stored': 8,
                'high_bit': 7,
                'pixel_representation': 0,
                'window_center': 40,
                'window_width': 400,
                'rescale_intercept': -1024,
                'rescale_slope': 1.0,
                'file_path': file_path
            }
            
            cursor.execute("""
                INSERT INTO viewer_dicomimage (
                    series_id, sop_instance_uid, instance_number,
                    file_path, rows, columns, pixel_spacing_x, pixel_spacing_y,
                    slice_thickness, window_width, window_center, processed_image_cache,
                    photometric_interpretation, pixel_spacing, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                series_id, image_data['sop_instance_uid'], image_data['instance_number'],
                image_data['file_path'], image_data['rows'], image_data['columns'],
                image_data['pixel_spacing_x'], image_data['pixel_spacing_y'],
                image_data['slice_thickness'], image_data['window_width'], image_data['window_center'],
                f"data:image/png;base64,{img_base64}",
                'MONOCHROME2', '0.5\\0.5',
                datetime.now().isoformat()
            ))
            
            print(f"✅ Created test image {i+1}/3")
        
        conn.commit()
        conn.close()
        
        print("🎉 Test data created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        return False

def main():
    print("🏥 DICOM Viewer Database Check and Fix")
    print("=" * 50)
    
    # Check current database state
    study_count, series_count, image_count = check_database()
    
    # Always create test data for now to ensure proper cached images
    print("\n🔧 Creating fresh test data with cached images...")
    
    if create_test_data():
        print("\n✅ Database updated with test data!")
        # Verify the fix
        print("\n🔍 Verifying fix...")
        check_database()
    else:
        print("\n❌ Failed to create test data")
        return 1
    
    print("\n🚀 You can now test the DICOM viewer!")
    return 0

if __name__ == '__main__':
    sys.exit(main())