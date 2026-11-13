#!/bin/sh
set -eu

LOG_FILE="/var/log/gateway/audit.log"
HEALTH_LOG="/var/log/gateway_health.log"
OUTPUT_FILE="/var/www/html/index.html"
TEMP_FILE="${OUTPUT_FILE}.tmp"

html_escape() {
    sed \
        -e 's/&/\&amp;/g' \
        -e 's/</\&lt;/g' \
        -e 's/>/\&gt;/g' \
        -e 's/"/\&quot;/g'
}

if [ -f "$LOG_FILE" ]; then
    latest_status="$(grep ' pico STAT ' "$LOG_FILE" | tail -n 1 || true)"
    recent_events="$(tail -n 50 "$LOG_FILE" | html_escape)"
else
    latest_status=""
    recent_events="Audit log is not available."
fi

if systemctl is-active --quiet gateway.service; then
    gateway_health="running"
else
    gateway_health="not running"
fi

if [ -f "$HEALTH_LOG" ]; then
    latest_healthcheck="$(tail -n 1 "$HEALTH_LOG" | html_escape)"
else
    latest_healthcheck="No health-check result is available."
fi

if [ -n "$latest_status" ]; then
    status_detail="$(printf '%s\n' "$latest_status" | sed 's/.* pico STAT //')"
else
    status_detail="No valid Pico status received yet."
fi

install -d -m 0755 "$(dirname "$OUTPUT_FILE")"
cat > "$TEMP_FILE" <<EOF
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="5">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gateway status</title>
  <style>
    body { font-family: sans-serif; margin: 2rem; }
    pre { background: #f3f3f3; padding: 1rem; overflow-x: auto; }
  </style>
</head>
<body>
  <h1>Gateway status</h1>
  <h2>Gateway service</h2>
  <pre>$(printf '%s\n' "$gateway_health" | html_escape)</pre>
  <h2>Latest health-check result</h2>
  <pre>$latest_healthcheck</pre>
  <h2>Latest Pico status</h2>
  <pre>$(printf '%s\n' "$status_detail" | html_escape)</pre>
  <h2>Recent events</h2>
  <pre>$recent_events</pre>
</body>
</html>
EOF
mv "$TEMP_FILE" "$OUTPUT_FILE"
