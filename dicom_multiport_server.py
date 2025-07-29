#!/usr/bin/env python3
"""
Multi-port DICOM SCP Server
Runs multiple DICOM servers on different ports for different facilities
"""

import os
import sys
import django
import logging
import threading
import signal
from time import sleep

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noctisview.settings')
django.setup()

from dicom_server import DicomServer
from viewer.models import Facility

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('dicom_multiport_server')

class MultiPortDicomServer:
    def __init__(self):
        self.servers = {}
        self.threads = {}
        self.running = True
        
    def generate_port_for_facility(self, facility):
        """Generate unique port for facility based on ID"""
        base_port = 11112
        return base_port + (facility.id % 1000)
    
    def start_server_for_facility(self, facility):
        """Start a DICOM server for a specific facility"""
        ae_title = DicomServer(None, None).generate_ae_title(facility.name)
        port = self.generate_port_for_facility(facility)
        
        server = DicomServer(ae_title=ae_title, port=port)
        
        # Override the facility mapping to only include this facility
        server.facility_ae_mapping = {ae_title: facility}
        
        def run_server():
            try:
                logger.info(f"Starting server for {facility.name} on port {port} with AE title {ae_title}")
                server.ae.start_server(('0.0.0.0', port), block=True)
            except Exception as e:
                logger.error(f"Error running server for {facility.name}: {e}")
        
        thread = threading.Thread(target=run_server, name=f"DICOM-{facility.name}")
        thread.daemon = True
        thread.start()
        
        self.servers[facility.id] = server
        self.threads[facility.id] = thread
        
        return port, ae_title
    
    def start_all_servers(self):
        """Start servers for all facilities"""
        facilities = Facility.objects.all()
        
        if not facilities:
            logger.warning("No facilities found in database")
            return
        
        logger.info(f"Starting DICOM servers for {len(facilities)} facilities")
        
        for facility in facilities:
            port, ae_title = self.start_server_for_facility(facility)
            logger.info(f"✓ {facility.name}: Port {port}, AE Title: {ae_title}")
        
        logger.info("\n" + "="*60)
        logger.info("All DICOM servers started successfully!")
        logger.info("="*60 + "\n")
        
        # Print configuration summary
        print("\n=== DICOM Server Configuration Summary ===\n")
        for facility in facilities:
            ae_title = DicomServer(None, None).generate_ae_title(facility.name)
            port = self.generate_port_for_facility(facility)
            print(f"{facility.name}:")
            print(f"  - AE Title: {ae_title}")
            print(f"  - Port: {port}")
            print(f"  - Configure your PACS to send to this port")
            print()
        
    def stop_all_servers(self):
        """Stop all running servers"""
        logger.info("Stopping all DICOM servers...")
        self.running = False
        
        # Note: pynetdicom servers don't have a clean shutdown method
        # The threads will stop when the main process exits
        
    def run(self):
        """Run the multi-port server"""
        self.start_all_servers()
        
        # Set up signal handlers
        def signal_handler(sig, frame):
            logger.info("Received shutdown signal")
            self.stop_all_servers()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Keep the main thread alive
        try:
            while self.running:
                sleep(1)
        except KeyboardInterrupt:
            self.stop_all_servers()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-port DICOM SCP Server')
    parser.add_argument('--list', action='store_true', help='List facility configurations')
    
    args = parser.parse_args()
    
    if args.list:
        facilities = Facility.objects.all()
        print("\n=== Facility DICOM Configurations ===\n")
        
        for facility in facilities:
            ae_title = DicomServer(None, None).generate_ae_title(facility.name)
            port = 11112 + (facility.id % 1000)
            
            print(f"Facility: {facility.name}")
            print(f"  - ID: {facility.id}")
            print(f"  - AE Title: {ae_title}")
            print(f"  - Port: {port}")
            print(f"  - Status: Active" if facility.is_active else "  - Status: Inactive")
            print()
    else:
        server = MultiPortDicomServer()
        server.run()


if __name__ == '__main__':
    main()