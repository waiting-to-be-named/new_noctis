# DICOM Server (SCP) Documentation

## Overview

The Noctis DICOM Viewer now includes a built-in DICOM SCP (Storage Class Provider) server that can receive DICOM images from remote facilities. The server automatically recognizes facilities based on their AE (Application Entity) titles and assigns them to the correct facility in the system.

## Features

- **Auto-generated AE Titles**: Each facility gets a unique AE title based on its name
- **Multi-port Support**: Different facilities can use different ports
- **Automatic Facility Recognition**: Incoming DICOM images are automatically assigned to the correct facility
- **Database Integration**: All received images are stored and indexed in the database
- **Support for Unknown Facilities**: Creates new facility entries for unknown AE titles

## Running the DICOM Server

### Option 1: Single Port Server

Run a single DICOM server on the default port (11112):

```bash
python3 manage.py run_dicom_server
```

With custom port and AE title:

```bash
python3 manage.py run_dicom_server --port 11115 --ae-title MY_SERVER
```

### Option 2: Multi-port Server

Run multiple servers, one for each facility:

```bash
python3 dicom_multiport_server.py
```

List all facility configurations:

```bash
python3 dicom_multiport_server.py --list
```

### Option 3: As a System Service

Install as a systemd service:

```bash
sudo cp noctis-dicom-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable noctis-dicom-server
sudo systemctl start noctis-dicom-server
```

Check service status:

```bash
sudo systemctl status noctis-dicom-server
```

## Facility Configuration

### View Facility DICOM Settings

To see the auto-generated AE titles and ports for all facilities:

```bash
python3 manage.py run_dicom_server --config
```

Or:

```bash
python3 dicom_server.py --config
```

### Example Output

```
=== Facility DICOM Configuration ===

Facility: Main Hospital
  AE Title: MAINHOSPITAL
  Port: 11113
  Server IP: <your-server-ip>
  Configuration for remote PACS:
    - Remote AE Title: MAINHOSPITAL
    - Remote IP: <your-server-ip>
    - Remote Port: 11113

Facility: City Clinic
  AE Title: CITYCLINIC
  Port: 11114
  Server IP: <your-server-ip>
  Configuration for remote PACS:
    - Remote AE Title: CITYCLINIC
    - Remote IP: <your-server-ip>
    - Remote Port: 11114
```

## Configuring Remote PACS/Modalities

To send images from a remote PACS or modality to Noctis:

1. Get the facility's configuration using the commands above
2. In your PACS/modality, add a new destination with:
   - **AE Title**: The auto-generated AE title for the facility
   - **IP Address**: Your Noctis server's IP address
   - **Port**: The assigned port for the facility
3. Test the connection using C-ECHO
4. Start sending images

## AE Title Generation Rules

AE titles are automatically generated from facility names:

1. Convert to uppercase
2. Remove all non-alphanumeric characters
3. Limit to 16 characters (DICOM standard)
4. If too short (< 4 chars), append a hash suffix

Examples:
- "Main Hospital" → "MAINHOSPITAL"
- "St. Mary's Clinic" → "STMARYSCLINIC"
- "Hospital Regional de São Paulo" → "HOSPITALREGIONAL"

## Storage Location

Received DICOM files are stored in:

```
/workspace/dicom_storage/
  └── <StudyInstanceUID>/
      └── <SeriesInstanceUID>/
          └── <SOPInstanceUID>.dcm
```

## Troubleshooting

### Check Server Logs

For single server:
```bash
tail -f /workspace/logs/dicom_server.log
```

For errors:
```bash
tail -f /workspace/logs/dicom_server_error.log
```

### Test Connectivity

Use the included SCU (Service Class User) to test:

```python
from dicom_server import DicomSCU

scu = DicomSCU()
# Test echo
success = scu.echo('REMOTE_AE', 'remote.ip.address', 11112)

# Send a file
success = scu.send_dicom('/path/to/file.dcm', 'REMOTE_AE', 'remote.ip.address', 11112)
```

### Common Issues

1. **Port Already in Use**: Make sure no other service is using the DICOM ports
2. **Permission Denied**: Run with appropriate permissions or use sudo
3. **Facility Not Recognized**: Check the AE title configuration in your PACS
4. **Images Not Appearing**: Check the upload_status in the database

## Security Considerations

1. **Firewall**: Only open DICOM ports to trusted IP addresses
2. **Authentication**: The current implementation accepts all connections. Consider adding IP-based filtering
3. **Encryption**: DICOM communication is unencrypted. Use VPN for sensitive data
4. **Storage**: Ensure adequate disk space for DICOM storage

## API Integration

The DICOM server automatically integrates with the existing Noctis API:

- Images appear in the worklist immediately after receipt
- Facility assignment is automatic based on AE title
- All existing viewer features work with received images

## Maintenance

### Clean Up Old Studies

To remove studies older than 90 days:

```python
from datetime import datetime, timedelta
from viewer.models import DicomStudy

cutoff_date = datetime.now() - timedelta(days=90)
old_studies = DicomStudy.objects.filter(created_at__lt=cutoff_date)
old_studies.delete()
```

### Monitor Disk Usage

```bash
du -sh /workspace/dicom_storage/
```

### Backup Configuration

The facility-to-AE mapping is stored in the database. Regular database backups will preserve this configuration.