import os
import sys
import time
import threading
from django.core.management.base import BaseCommand
from django.conf import settings
from dicom_server.server import NoctisDicomServer


class Command(BaseCommand):
    help = 'Start the DICOM SCP/SCU server'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=None,
            help='Port to run the server on (default: from database config)'
        )
        parser.add_argument(
            '--ae-title',
            type=str,
            default=None,
            help='AE Title for the server (default: from database config)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Noctis DICOM Server...')
        )
        
        # Create DICOM files directory if it doesn't exist
        dicom_dir = os.path.join(settings.BASE_DIR, 'dicom_files')
        os.makedirs(dicom_dir, exist_ok=True)
        
        # Initialize server
        server = NoctisDicomServer()
        
        # Override config if provided
        if options['port']:
            server.config.port = options['port']
        if options['ae_title']:
            server.config.ae_title = options['ae_title']
        
        # Enable debug logging if requested
        if options['debug']:
            from pynetdicom import debug_logger
            debug_logger()
            self.stdout.write(
                self.style.WARNING('Debug logging enabled')
            )
        
        try:
            # Start server
            if server.start_server():
                self.stdout.write(
                    self.style.SUCCESS(
                        f'DICOM server started successfully on port {server.config.port}'
                    )
                )
                self.stdout.write(
                    f'AE Title: {server.config.ae_title}'
                )
                self.stdout.write(
                    'Press Ctrl+C to stop the server'
                )
                
                # Keep server running
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    self.stdout.write(
                        self.style.WARNING('\nStopping DICOM server...')
                    )
                    server.stop_server()
                    self.stdout.write(
                        self.style.SUCCESS('DICOM server stopped')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR('Failed to start DICOM server')
                )
                sys.exit(1)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error starting DICOM server: {e}')
            )
            sys.exit(1)