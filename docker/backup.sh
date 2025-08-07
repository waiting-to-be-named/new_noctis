#!/bin/sh
# Backup script for NOCTIS DICOM Viewer

set -e

# Configuration
BACKUP_DIR="/backups"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-noctis_db}"
DB_USER="${DB_USER:-noctis_user}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}/database"
mkdir -p "${BACKUP_DIR}/dicom"

echo "Starting backup at ${TIMESTAMP}"

# Database backup
echo "Backing up database..."
PGPASSWORD="${DB_PASSWORD}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -f "${BACKUP_DIR}/database/noctis_db_${TIMESTAMP}.sql" \
    --verbose \
    --no-owner \
    --no-privileges

# Compress database backup
gzip "${BACKUP_DIR}/database/noctis_db_${TIMESTAMP}.sql"
echo "Database backup completed: noctis_db_${TIMESTAMP}.sql.gz"

# DICOM files backup (if directory exists and has files)
if [ -d "/app/media/dicom_files" ] && [ "$(ls -A /app/media/dicom_files)" ]; then
    echo "Backing up DICOM files..."
    tar -czf "${BACKUP_DIR}/dicom/dicom_files_${TIMESTAMP}.tar.gz" \
        -C /app/media dicom_files
    echo "DICOM files backup completed: dicom_files_${TIMESTAMP}.tar.gz"
else
    echo "No DICOM files to backup"
fi

# Clean up old backups
echo "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
find "${BACKUP_DIR}/database" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}/dicom" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete

# List current backups
echo "Current backups:"
ls -lh "${BACKUP_DIR}/database/"*.sql.gz 2>/dev/null || echo "No database backups found"
ls -lh "${BACKUP_DIR}/dicom/"*.tar.gz 2>/dev/null || echo "No DICOM backups found"

echo "Backup completed successfully at $(date)"

# Optional: Upload to cloud storage (S3, Google Cloud Storage, etc.)
# Uncomment and configure as needed
# if [ -n "${AWS_ACCESS_KEY_ID}" ]; then
#     echo "Uploading to S3..."
#     aws s3 cp "${BACKUP_DIR}/database/noctis_db_${TIMESTAMP}.sql.gz" \
#         "s3://${S3_BUCKET}/backups/database/" --storage-class GLACIER
#     aws s3 cp "${BACKUP_DIR}/dicom/dicom_files_${TIMESTAMP}.tar.gz" \
#         "s3://${S3_BUCKET}/backups/dicom/" --storage-class GLACIER
# fi