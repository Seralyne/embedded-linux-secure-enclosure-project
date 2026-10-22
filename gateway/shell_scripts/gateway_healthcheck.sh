#!/bin/bash
# Check if the gateway systemd unit is actively running
if systemctl is-active --quiet gateway.service; then
    echo "$(date -Iseconds) - HEALTH CHECK: Gateway service is running normally."
    exit 0
else
    echo "$(date -Iseconds) - HEALTH CHECK CRITICAL: Gateway service is STOPPED." >&2
    exit 1
fi
