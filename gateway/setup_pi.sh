#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script with sudo or as root." >&2
    exit 1
fi

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
INSTALL_DIR="/opt/gateway"
SCRIPT_DIR="$INSTALL_DIR/scripts"
VENV_DIR="$INSTALL_DIR/venv"
SYSTEMD_DIR="/etc/systemd/system"
JOURNALD_DIR="/etc/systemd/journald.conf.d"
DEFAULTS_FILE="/etc/default/gateway"

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

require_command python3
require_command systemctl
require_command install
require_command chattr

if ! systemctl cat mosquitto.service >/dev/null 2>&1; then
    echo "Mosquitto is not installed. Install mosquitto before deploying the gateway." >&2
    exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "The Python venv module is missing. Install python3-venv first." >&2
    exit 1
fi

install -d -m 0755 "$INSTALL_DIR" "$SCRIPT_DIR"
install -m 0755 "$REPO_DIR/gateway/gateway.py" "$INSTALL_DIR/gateway.py"
install -m 0755 "$REPO_DIR/gateway/shell_scripts/gateway_healthcheck.sh" "$SCRIPT_DIR/gateway_healthcheck.sh"
install -m 0755 "$REPO_DIR/gateway/shell_scripts/gateway_rotate.sh" "$SCRIPT_DIR/gateway_rotate.sh"
install -m 0755 "$REPO_DIR/gateway/shell_scripts/gateway_log_setup.sh" "$SCRIPT_DIR/gateway_log_setup.sh"
install -m 0755 "$REPO_DIR/gateway/shell_scripts/gateway_status_page.sh" "$SCRIPT_DIR/gateway_status_page.sh"

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --disable-pip-version-check paho-mqtt pyserial

for unit in \
    gateway.service \
    gateway_healthcheck.service \
    gateway_healthcheck.timer \
    gateway_rotate.service \
    gateway_rotate.timer \
    gateway_status_page.service \
    gateway_status_page.timer
do
    install -m 0644 "$REPO_DIR/config/gateway/$unit" "$SYSTEMD_DIR/$unit"
done

install -d -m 0755 "$JOURNALD_DIR"
install -m 0644 \
    "$REPO_DIR/config/gateway/journald.conf.d/99-gateway-persistent.conf" \
    "$JOURNALD_DIR/99-gateway-persistent.conf"

if [ ! -f "$DEFAULTS_FILE" ]; then
    printf '%s\n' 'GATEWAY_SERIAL_PORT=/dev/serial0' > "$DEFAULTS_FILE"
    chmod 0644 "$DEFAULTS_FILE"
fi

"$SCRIPT_DIR/gateway_log_setup.sh"

systemctl daemon-reload
systemctl restart systemd-journald
systemctl enable --now mosquitto.service
systemctl enable gateway.service gateway_healthcheck.timer gateway_rotate.timer gateway_status_page.timer
systemctl restart gateway.service
systemctl restart gateway_healthcheck.timer gateway_rotate.timer gateway_status_page.timer

if command -v lighttpd >/dev/null 2>&1; then
    systemctl enable --now lighttpd
else
    echo "lighttpd is not installed; install it before using the status page." >&2
fi

echo "Gateway deployment completed."
echo "Serial port: $(sed -n 's/^GATEWAY_SERIAL_PORT=//p' "$DEFAULTS_FILE")"
echo "Audit log: /var/log/gateway/audit.log"
echo "Status page: /var/www/html/index.html"
