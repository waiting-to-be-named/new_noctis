# DICOM SCP Server Guide

## Overview

The Noctis DICOM SCP server allows remote facilities to send DICOM images directly to the system. The server automatically recognizes facilities by their AE titles and routes images appropriately.

## Features

- **Automatic Facility Recognition**: Each facility gets a unique AE title and can send images using their designated AE title
- **Multi-Modal Support**: Supports CT, MR, XR, US, CR, and other DICOM modalities
- **Auto-Generated Configuration**: AE titles and ports are automatically generated for each facility
- **Database Integration**: Received images are automatically stored in the database and file system
- **C-ECHO Support**: Server responds to verification requests
- **Robust Error Handling**: Graceful handling of malformed or incomplete DICOM data

## Quick Start

### 1. Install Dependencies

Make sure you have installed all required packages:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Database Migrations

Create the database tables including the new DICOM port field:

```bash
source venv/bin/activate
python manage.py migrate
```

### 3. Create Facilities

Before starting the server, create facilities in the Django admin:

1. Go to Django admin: `http://localhost:8000/admin/`
2. Navigate to "Facilities" 
3. Create a new facility - the AE title and DICOM port will be auto-generated
4. Note the generated AE title for configuration on the remote system

### 4. Start the DICOM Server

#### Option A: Using the Management Command

```bash
source venv/bin/activate
python manage.py start_dicom_server --port 11112 --ae-title NOCTIS_SERVER
```

#### Option B: Using the Standalone Script

```bash
source venv/bin/activate
python start_dicom_server.py --port 11112 --ae-title NOCTIS_SERVER
```

#### Command Line Options

- `--port`: Port to listen on (default: 11112)
- `--ae-title`: Server AE title (default: NOCTIS_SERVER) 
- `--debug`: Enable debug logging

## Configuration

### Facility AE Titles

Each facility automatically gets:
- **AE Title**: Auto-generated based on facility name (16 characters max)
- **DICOM Port**: Auto-assigned unique port number (starting from 11112)

Example:
- Facility: "Central Hospital"
- Generated AE Title: "CENTRALHOSP1A2B"
- Assigned Port: 11113

### Remote System Configuration

Configure your PACS or imaging equipment to send to:
- **Server IP**: Your server's IP address
- **Server Port**: 11112 (or the port you specified)
- **Server AE Title**: NOCTIS_SERVER (or the AE title you specified)
- **Calling AE Title**: Your facility's auto-generated AE title

## Supported DICOM Services

### C-STORE (Storage)

The server accepts DICOM images via C-STORE and automatically:
1. Identifies the sending facility by AE title
2. Creates/updates study, series, and image records in the database
3. Stores DICOM files in `media/dicom_files/`
4. Associates images with the correct facility

### C-ECHO (Verification)

The server responds to C-ECHO requests for connectivity testing.

### Supported SOP Classes

- CT Image Storage
- MR Image Storage
- X-Ray Angiographic Image Storage
- Digital X-Ray Image Storage (Presentation/Processing)
- Computed Radiography Image Storage
- Ultrasound Image Storage
- Secondary Capture Image Storage
- And more...

## File Storage

DICOM files are stored in:
```
media/
└── dicom_files/
    ├── [SOPInstanceUID1].dcm
    ├── [SOPInstanceUID2].dcm
    └── ...
```

Each file is named using its SOP Instance UID for uniqueness.

## Database Integration

Received images automatically create/update:

1. **DicomStudy**: Patient and study information
2. **DicomSeries**: Series-level metadata
3. **DicomImage**: Individual image records
4. **Facility Association**: Links studies to the sending facility

## Monitoring

### Server Logs

The server logs all activities including:
- Incoming connections
- Facility recognition
- File storage status
- Error conditions

### Admin Interface

Monitor received studies through:
- Django Admin → DICOM Studies
- View facility-specific data
- Check study completion status

## Troubleshooting

### Common Issues

1. **"No facility found for AE title"**
   - Check that the facility exists in the database
   - Verify the AE title matches exactly
   - Case-sensitive matching

2. **"Permission denied" errors**
   - Check file system permissions for media directory
   - Ensure Python process can write to media/dicom_files/

3. **"Port already in use"**
   - Change the port number using `--port` option
   - Check for other DICOM services running

### Testing Connectivity

Test server connectivity using a DICOM client:

```bash
# Using dcmtk tools (if installed)
echoscu <server_ip> 11112 -aet YOUR_AE_TITLE -aec NOCTIS_SERVER
```

## Security Considerations

- The server accepts connections from any IP address
- Consider firewall rules to restrict access
- AE title-based facility identification provides basic access control
- Monitor logs for unexpected connections

## Production Deployment

For production use:

1. **Use a process manager** (systemd, supervisor)
2. **Configure firewall** rules
3. **Set up log rotation**
4. **Monitor disk space** for DICOM file storage
5. **Regular database backups**

## Example systemd Service

Create `/etc/systemd/system/noctis-dicom.service`:

```ini
[Unit]
Description=Noctis DICOM SCP Server
After=network.target

[Service]
Type=exec
User=noctis
WorkingDirectory=/path/to/noctis
ExecStart=/path/to/noctis/venv/bin/python start_dicom_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable noctis-dicom
sudo systemctl start noctis-dicom
```

## Support

For issues or questions:
1. Check the server logs
2. Verify facility configuration in Django admin
3. Test with C-ECHO first
4. Review network connectivity between systems