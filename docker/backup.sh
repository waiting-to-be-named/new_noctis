#!/bin/bash

# Automated backup script for Noctis DICOM Viewer
# Runs inside the backup container

set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
DB_HOST=${DB_HOST:-db}
DB_NAME=${POSTGRES_DB:-noctis}
DB_USER=${POSTGRES_USER:-noctis}

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [BACKUP] $1"
}

# Ensure backup directory exists
mkdir -p $BACKUP_DIR

# Database backup
log "Starting database backup..."
if pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME | gzip > $BACKUP_DIR/noctis_db_$DATE.sql.gz; then
    log "Database backup completed: noctis_db_$DATE.sql.gz"
else
    log "ERROR: Database backup failed"
    exit 1
fi

# Remove old backups
log "Cleaning up old backups (retention: ${RETENTION_DAYS} days)..."
find $BACKUP_DIR -name "noctis_db_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete

# Log backup statistics
BACKUP_SIZE=$(du -h $BACKUP_DIR/noctis_db_$DATE.sql.gz | cut -f1)
TOTAL_BACKUPS=$(find $BACKUP_DIR -name "noctis_db_*.sql.gz" -type f | wc -l)
log "Backup size: $BACKUP_SIZE, Total backups: $TOTAL_BACKUPS"

log "Backup process completed successfully"

# Add to cron if not already present
if [ ! -f /var/spool/cron/crontabs/root ]; then
    # Daily backup at 2 AM
    echo "0 2 * * * /backup.sh" | crontab -
    log "Backup cron job installed"
fi