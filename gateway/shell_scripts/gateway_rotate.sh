#!/bin/bash
LOG_FILE="/var/log/gateway_audit.log"
BACKUP_FILE="/var/log/gateway_audit.log.1"

if [ -f "$LOG_FILE" ]; then
    # 1. Temporarily lift the append-only attribute
    sudo chattr -a "$LOG_FILE"
    
    # 2. Cycle the logs out
    if [ -f "$BACKUP_FILE" ]; then
        sudo rm "$BACKUP_FILE"
    fi
    sudo mv "$LOG_FILE" "$BACKUP_FILE"
    
    # 3. Create a fresh file and re-apply append-only safety
    sudo touch "$LOG_FILE"
    sudo chmod 666 "$LOG_FILE"
    sudo chattr +a "$LOG_FILE"
    
    echo "$(date -Iseconds) - LOG ROTATION: Log successfully rotated."
else
    echo "$(date -Iseconds) - LOG ROTATION ERROR: Target log file not found." >&2
fi
