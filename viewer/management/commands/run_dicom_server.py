from django.core.management.base import BaseCommand
from django.conf import settings
import sys
import os

# Add parent directory to path to import dicom_server
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from dicom_server import DicomServer, generate_facility_config


class Command(BaseCommand):
    help = 'Run the DICOM SCP server to receive images from remote facilities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=11112,
            help='Port to listen on (default: 11112)',
        )
        parser.add_argument(
            '--ae-title',
            default='NOCTIS_SCP',
            help='AE Title for the server (default: NOCTIS_SCP)',
        )
        parser.add_argument(
            '--config',
            action='store_true',
            help='Show facility configuration instead of running server',
        )

    def handle(self, *args, **options):
        if options['config']:
            generate_facility_config()
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Starting DICOM SCP server on port {options['port']} with AE title {options['ae_title']}"
            ))
            
            server = DicomServer(ae_title=options['ae_title'], port=options['port'])
            
            try:
                server.start()
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("Server stopped by user"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Server error: {e}"))