from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage
from django.conf import settings

import os
import uuid
import logging
import threading
import time

import pydicom

from viewer.models import Facility, DicomStudy, DicomSeries, DicomImage

try:
    from pynetdicom import AE, evt
    from pynetdicom.sop_class import StoragePresentationContexts
except ImportError as e:
    raise ImportError("pynetdicom is required for the DICOM SCP server. Please install it by adding 'pynetdicom' to requirements.txt") from e

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Run a DICOM Storage SCP that routes incoming associations based on calling AE title."""

    help = "Run a DICOM Storage SCP that stores incoming images and associates them with facilities based on AE Title."

    def add_arguments(self, parser):
        parser.add_argument(
            '--port', type=int, default=None,
            help='Run a single SCP on the specified port instead of starting a server for every facility.',
        )
        parser.add_argument(
            '--ae-title', type=str, default='NOCTISVIEW',
            help='AE Title of this SCP when running a single instance (default: NOCTISVIEW)'
        )

    # ---------------------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------------------
    def _store_dataset(self, ds, facility=None):
        """Persist the received dataset and create DB entries (very similar to the upload logic)."""
        # Prepare storage path
        filename = f"{uuid.uuid4()}.dcm"
        relative_path = os.path.join(settings.DICOM_UPLOAD_PATH, filename) if hasattr(settings, 'DICOM_UPLOAD_PATH') else f'dicom_files/{filename}'
        full_path = default_storage.path(relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        ds.save_as(full_path, write_like_original=False)

        # -----------------------------------------------------------------
        # Minimal database persistence (we only create the study+series+image
        # structure if it does not exist yet). Detailed extraction logic is
        # kept intentionally light so the SCP remains responsive. You can
        # re-use the comprehensive extraction functions in viewer.views if
        # you need richer metadata.
        # -----------------------------------------------------------------
        study_uid = str(ds.get('StudyInstanceUID', '')) or f"STUDY_{uuid.uuid4()}"
        series_uid = str(ds.get('SeriesInstanceUID', '')) or f"SERIES_{uuid.uuid4()}"
        sop_uid = str(ds.get('SOPInstanceUID', uuid.uuid4()))

        # Patient info – fallbacks if missing
        patient_name = str(ds.get('PatientName', 'Unknown'))
        patient_id = str(ds.get('PatientID', 'Unknown'))
        modality = str(ds.get('Modality', 'OT'))

        study, _ = DicomStudy.objects.get_or_create(
            study_instance_uid=study_uid,
            defaults={
                'patient_name': patient_name,
                'patient_id': patient_id,
                'modality': modality,
                'facility': facility,
            }
        )

        series, _ = DicomSeries.objects.get_or_create(
            study=study, series_instance_uid=series_uid,
            defaults={'modality': modality, 'series_number': int(ds.get('SeriesNumber', 0))}
        )

        # Finally save the image object
        DicomImage.objects.get_or_create(
            series=series,
            sop_instance_uid=sop_uid,
            defaults={
                'instance_number': int(ds.get('InstanceNumber', 0)),
                'file_path': relative_path,
            }
        )

    # ------------------------------------------------------------------
    # pynetdicom event handlers
    # ------------------------------------------------------------------
    def _handle_store(self, event, facility_resolver):
        """pynetdicom EVT_C_STORE handler."""
        try:
            ds = event.dataset
            ds.file_meta = event.file_meta

            calling_ae = event.assoc.requestor.ae_title.decode('ascii').strip()
            facility = facility_resolver(calling_ae)

            self._store_dataset(ds, facility=facility)
            logger.info("Stored SOP Instance %s from AE %s", ds.SOPInstanceUID, calling_ae)
            return 0x0000  # Success
        except Exception as exc:
            logger.exception("Failed to store incoming dataset: %s", exc)
            return 0xA700  # Out of resources (processing failure)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        port_arg = options['port']
        ae_title = options['ae_title']

        if port_arg:
            # Single server mode
            self.stdout.write(self.style.SUCCESS(f"Starting single DICOM SCP on port {port_arg} (AE Title: {ae_title})"))
            self._start_server(port_arg, ae_title)
        else:
            # Multi-facility mode – spin up one thread per facility that has a unique port defined.
            facilities = Facility.objects.exclude(dicom_port__isnull=True).exclude(ae_title__isnull=True)
            if not facilities:
                raise CommandError("No facilities with AE Title and DICOM port defined. Please create at least one Facility.")

            self.stdout.write(self.style.SUCCESS("Starting DICOM SCP servers for all facilities:"))
            for facility in facilities:
                self.stdout.write(f"  • {facility.name}: AE={facility.ae_title} PORT={facility.dicom_port}")
                threading.Thread(target=self._start_server, args=(facility.dicom_port, facility.ae_title), daemon=True).start()

            # Keep the management command alive
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("Shutting down DICOM servers…"))

    # ------------------------------------------------------------------
    def _start_server(self, port, ae_title):
        ae = AE(ae_title=ae_title)
        for cx in StoragePresentationContexts:
            ae.add_supported_context(cx.abstract_syntax, cx.transfer_syntax)

        # The resolver maps calling AE title to Facility instance (or None)
        facility_resolver = lambda calling_ae: Facility.objects.filter(ae_title=calling_ae).first()

        handlers = [(evt.EVT_C_STORE, lambda e, _sr=facility_resolver: self._handle_store(e, _sr))]

        try:
            ae.start_server(('0.0.0.0', port), block=True, evt_handlers=handlers)
        except Exception as exc:
            logger.exception("Failed to start DICOM SCP on port %s: %s", port, exc)