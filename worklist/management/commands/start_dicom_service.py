"""
Django management command to start the DICOM networking service
Usage: python manage.py start_dicom_service
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from worklist.dicom_networking import start_dicom_service, get_dicom_service_status
import time

class Command(BaseCommand):
    help = 'Start the DICOM networking service to receive data from remote modalities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=getattr(settings, 'DICOM_PORT', 11112),
            help='DICOM port to listen on (default: 11112)'
        )
        parser.add_argument(
            '--ae-title',
            type=str,
            default=getattr(settings, 'DICOM_AE_TITLE', 'NOCTIS_PACS'),
            help='DICOM Application Entity Title (default: NOCTIS_PACS)'
        )
        parser.add_argument(
            '--host',
            type=str,
            default=getattr(settings, 'DICOM_HOST', '0.0.0.0'),
            help='Host to bind to (default: 0.0.0.0)'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.HTTP_INFO('Starting NOCTIS DICOM Networking Service...')
        )
        
        # Display configuration
        self.stdout.write(f"AE Title: {options['ae_title']}")
        self.stdout.write(f"Host: {options['host']}")
        self.stdout.write(f"Port: {options['port']}")
        
        # Start the service
        success = start_dicom_service()
        
        if success:
            self.stdout.write(
                self.style.SUCCESS('✅ DICOM service started successfully!')
            )
            self.stdout.write(
                self.style.HTTP_INFO('🏥 Ready to receive DICOM data from remote modalities')
            )
            self.stdout.write(
                self.style.HTTP_INFO('📡 Configure your modalities to send to:')
            )
            self.stdout.write(f"   Host: {options['host']}")
            self.stdout.write(f"   Port: {options['port']}")
            self.stdout.write(f"   AE Title: {options['ae_title']}")
            
            # Keep the command running and show status updates
            try:
                while True:
                    time.sleep(30)  # Check status every 30 seconds
                    status = get_dicom_service_status()
                    if status['received_instances_count'] > 0:
                        self.stdout.write(
                            f"📊 Received {status['received_instances_count']} DICOM instances"
                        )
                        if status['last_received']:
                            last = status['last_received']
                            self.stdout.write(
                                f"🔄 Last: {last['study']} - {last['series']} "
                                f"(Instance {last['instance']}) at {last['timestamp']}"
                            )
            except KeyboardInterrupt:
                self.stdout.write(
                    self.style.WARNING('\n🛑 Stopping DICOM service...')
                )
                
        else:
            self.stdout.write(
                self.style.ERROR('❌ Failed to start DICOM service')
            )
            self.stdout.write(
                self.style.ERROR('Check that pynetdicom is installed: pip install pynetdicom')
            )
            self.stdout.write(
                self.style.ERROR('Check that the port is not already in use')
            )