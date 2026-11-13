#!/bin/sh
set -eu

LOG_DIR="/var/log/gateway"
LOG_FILE="$LOG_DIR/audit.log"

install -d -m 0755 "$LOG_DIR"
touch "$LOG_FILE"
chattr -a "$LOG_FILE"
chmod 0640 "$LOG_FILE"
chattr +a "$LOG_FILE"

echo "$(date -Iseconds) gateway LOG_READY path=$LOG_FILE append_only=true"
