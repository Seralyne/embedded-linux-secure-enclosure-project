#!/bin/bash
LOG_FILE="/var/log/gateway/audit.log"
BACKUP_FILE="/var/log/gateway/audit.log.1"

if [ -f "$LOG_FILE" ]; then
    # 1. Temporarily lift the append-only attribute
    chattr -a "$LOG_FILE"
    
    # 2. Cycle the logs out
    if [ -f "$BACKUP_FILE" ]; then
        rm "$BACKUP_FILE"
    fi
    mv "$LOG_FILE" "$BACKUP_FILE"
    
    # 3. Create a fresh file and re-apply append-only safety
    touch "$LOG_FILE"
    chmod 640 "$LOG_FILE"
    chattr +a "$LOG_FILE"
    
    echo "$(date -Iseconds) - LOG ROTATION: Log successfully rotated."
else
    echo "$(date -Iseconds) - LOG ROTATION ERROR: Target log file not found." >&2
fi
