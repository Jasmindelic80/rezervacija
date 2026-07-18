#!/bin/bash

DATE=$(date +%Y-%m-%d_%H-%M)
BACKUP_DIR="/var/backups/bookbih"
DB_NAME="bookbih"
DB_USER="mojauser"
MEDIA_DIR="/var/www/bookbih/media"
DRIVE_FOLDER="googledrive:BookBiH-Backup"
LOG_FILE="/var/log/bookbih-backup.log"

echo "=== Backup started: $DATE ===" >> $LOG_FILE

mkdir -p $BACKUP_DIR

# 1. Backup baze
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz
echo "✓ Database backup OK" >> $LOG_FILE

# 2. Backup media fajlova
tar -czf $BACKUP_DIR/media_$DATE.tar.gz $MEDIA_DIR 2>/dev/null
echo "✓ Media backup OK" >> $LOG_FILE

# 3. Upload na Google Drive
rclone copy $BACKUP_DIR/db_$DATE.sql.gz $DRIVE_FOLDER/
rclone copy $BACKUP_DIR/media_$DATE.tar.gz $DRIVE_FOLDER/
echo "✓ Google Drive upload OK" >> $LOG_FILE

# 4. Obrisi lokalne starije od 7 dana
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
echo "✓ Old backups cleaned" >> $LOG_FILE

echo "=== Backup finished: $(date +%Y-%m-%d_%H-%M) ===" >> $LOG_FILE
echo "" >> $LOG_FILE
