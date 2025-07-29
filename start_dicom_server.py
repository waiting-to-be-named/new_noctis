#!/usr/bin/env python3
"""
Simple script to start the DICOM SCP server
Usage: python start_dicom_server.py [--port PORT] [--ae-title AE_TITLE]
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to the path
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

# Now we can import Django models and management command
from django.core.management import call_command
import argparse

def main():
    parser = argparse.ArgumentParser(description='Start DICOM SCP Server')
    parser.add_argument('--port', type=int, default=11112, help='Port to listen on (default: 11112)')
    parser.add_argument('--ae-title', type=str, default='NOCTIS_SERVER', help='AE Title for the server (default: NOCTIS_SERVER)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    print(f"Starting DICOM SCP Server...")
    print(f"Port: {args.port}")
    print(f"AE Title: {args.ae_title}")
    print(f"Debug: {args.debug}")
    print("")
    print("The server will automatically recognize facility AE titles and route DICOM images accordingly.")
    print("Press Ctrl+C to stop the server.")
    print("="*60)
    
    # Call the Django management command
    call_command('start_dicom_server', 
                port=args.port, 
                ae_title=args.ae_title,
                debug=args.debug)

if __name__ == '__main__':
    main()