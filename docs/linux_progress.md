# Linux-owner implementation notes

This follows the phases and terminology in the build guide. It records the
Linux work currently implemented in the repository, plus the Pi-side checks
that still need to be run.

## Phase 5: practise the Linux side in a VM

### Gateway implementation

[`gateway/gateway.py`](../gateway/gateway.py) is now the single process that
owns both the Pico serial link and the MQTT client.

The original serial behavior remains in the main loop:

- Read one line from the serial port.
- Verify the Pico protocol's NMEA-style XOR checksum.
- Parse valid Pico messages.
- Send a heartbeat every second.

The gateway now also:

- Publishes valid `$STAT` messages as JSON.
- Publishes valid `$ALRM` messages as JSON.
- Subscribes to the command topic.
- Validates MQTT relay commands before forwarding them.
- Builds checksummed `$CMD` messages for the Pico.
- Maintains a wrapping 0–65535 counter for outgoing messages.

The serial port is configurable through the environment:

```text
GATEWAY_SERIAL_PORT=/dev/serial0
```

The development default remains `/dev/pts/3`.

### Audit format

Gateway log messages use the format required by the guide:

```text
time source event detail
```

The gateway records:

- Startup and shutdown.
- Valid Pico `STAT` messages.
- Valid Pico `ALRM` messages.
- Rejected Pico messages.
- Accepted and rejected MQTT commands.
- MQTT connection failures.
- Outgoing heartbeats.

### systemd and housekeeping

The gateway service is defined in
[`config/gateway/gateway.service`](../config/gateway/gateway.service). It:

- Runs `/opt/gateway/gateway.py`.
- Requires `mosquitto.service`.
- Starts after Mosquitto.
- Loads `/etc/default/gateway`.
- Restarts the process after failure.
- Redirects stdout and stderr to `/var/log/gateway/audit.log`.

The repository also contains:

- `gateway_healthcheck.service` and `.timer`.
- `gateway_rotate.service` and `.timer`.
- [`gateway_healthcheck.sh`](../gateway/shell_scripts/gateway_healthcheck.sh).
- [`gateway_rotate.sh`](../gateway/shell_scripts/gateway_rotate.sh).

The VM systemd recovery test and timer tests still need to be run and
recorded.

### Services enabled at boot

`setup_pi.sh` enables these units:

| Unit | Autostart behavior |
|---|---|
| `gateway.service` | Starts at boot and restarts if the gateway exits |
| `gateway_healthcheck.timer` | Starts at boot; runs the health check one minute after boot and every five minutes |
| `gateway_rotate.timer` | Starts at boot; runs log rotation nightly at midnight |
| `gateway_status_page.timer` | Starts at boot; refreshes the HTML page after 30 seconds and every five seconds |

The corresponding `.service` files for the timers are oneshot services. They
are started by their timers rather than enabled independently.

`systemd-journald` is a built-in system service. The deployment script installs
its persistent-storage configuration and restarts it; it does not need a
separate project enablement step.

Mosquitto must be installed before deployment. `setup_pi.sh` verifies that the
unit exists and enables/starts it:

```sh
sudo systemctl enable --now mosquitto
```

Lighttpd is also outside the gateway service group. If installed, the setup
script enables and starts it.

Verify the project units with:

```sh
systemctl is-enabled gateway.service
systemctl is-enabled gateway_healthcheck.timer
systemctl is-enabled gateway_rotate.timer
systemctl is-enabled gateway_status_page.timer
systemctl status gateway.service
systemctl list-timers --all | grep -E 'gateway|mosquitto'
```

## Phase 6: bring up the Raspberry Pi

The following Pi bring-up work has been completed:

- The RTC has been connected and configured.
- The serial console has been disabled.
- The hardware UART has been enabled.
- SSH key-based access has been set up.

SSH security hardening has **not** been done yet. Password-login restrictions,
root-login restrictions, and allowed-user restrictions remain Phase 9 work. Root user does not have password. Use public key with its password, as given to you on the USB drive last time.

The repository also includes a deployment script:

[`gateway/setup_pi.sh`](../gateway/setup_pi.sh)

This is a new script in the repository; it is not a pre-installed Pi
command. It must be run from a checkout of this repository, or copied to the
Pi together with the files it references.

When run as root, it installs:

- `/opt/gateway/gateway.py`
- `/opt/gateway/scripts/`
- A Python virtual environment
- `paho-mqtt`
- `pyserial`
- The gateway systemd units and timers
- Persistent journald configuration
- The append-only audit log

The script does **not**:

- Install lighttpd.
- Configure the firewall.
- Configure SSH security hardening.
- Create TLS certificates.
- Configure Mosquitto TLS or ACLs.
- Change the existing RTC, serial-console, or UART settings.

Run it from the repository root on the Pi:

```sh
sudo ./gateway/setup_pi.sh
```

The script performs the following sequence:

1. Checks that it is running as root and that required commands exist.
2. Copies `gateway.py` to `/opt/gateway/gateway.py`.
3. Copies the shell helpers to `/opt/gateway/scripts/`.
4. Creates `/opt/gateway/venv/`.
5. Installs `paho-mqtt` and `pyserial` into that virtual environment.
6. Copies the gateway services and timers into `/etc/systemd/system/`.
7. Copies the persistent-journald drop-in into
   `/etc/systemd/journald.conf.d/`.
8. Creates `/etc/default/gateway` if it does not already exist, with:

```text
GATEWAY_SERIAL_PORT=/dev/serial0
```

9. Creates the audit-log directory and enables append-only logging.
10. Reloads systemd and restarts journald.
11. Enables and starts the gateway, health-check, rotation, and status-page
    timers.
12. Enables lighttpd only if it is already installed.

The script is intended to be rerunnable. It does not overwrite an existing
`/etc/default/gateway`, so a manually chosen serial port is preserved.

After deployment, `/dev/serial0` still needs to be confirmed as the UART
connected to the Pico.

This script has already been run on the Pi.

## Phase 7: connect the Pi and Pico

The gateway is prepared to:

- Send the documented `$HB,<counter>,NET=OK*CS` heartbeat.
- Record Pico status in the audit log.
- Forward validated relay commands to the Pico.
- Record Pico alarms and rejected messages.

The real serial-link test has not yet been run. In particular, the following
still need confirmation on hardware:

- Pico receives heartbeats.
- Status appears in the audit log.
- The expected normal LED state occurs.
- Loss of the serial link produces the expected safe state.

## Phase 8: unencrypted MQTT

The topic names and payload formats are documented in
[`docs/protocol.md`](protocol.md).

Configured topics:

| Topic | Gateway behavior |
|---|---|
| `site/gateway-01/status` | Publishes JSON converted from valid `$STAT` |
| `site/gateway-01/alarm` | Publishes JSON converted from valid `$ALRM` |
| `site/gateway-01/cmd` | Subscribes and validates relay commands |

Status example:

```json
{"type":"STAT","counter":120,"door":0,"light":12,"relay":1,"state":"OK"}
```

Alarm example:

```json
{"type":"ALRM","counter":121,"reason":"DOOR"}
```

Accepted command shapes are exactly:

```json
{"relay":0}
```

```json
{"relay":1}
```

The gateway rejects malformed JSON, extra fields, boolean values, and relay
values other than 0 or 1. Valid commands are converted to checksummed Pico
messages.

Mosquitto and the Mosquitto client tools have been installed on the Pi.
The following end-to-end checks remain:

```sh
mosquitto_sub -h localhost -t 'site/#' -v
```

Then publish a command from the operator laptop and confirm that the relay
responds.

## Phase 9: security hardening and TLS

No work on Phase 9 has been done.

## Phase 11: audit log and local web page

### Append-only audit log

[`gateway_log_setup.sh`](../gateway/shell_scripts/gateway_log_setup.sh):

- Creates `/var/log/gateway/audit.log`.
- Sets mode `0640`.
- Enables the append-only filesystem attribute.

[`gateway_rotate.sh`](../gateway/shell_scripts/gateway_rotate.sh):

- Removes the append-only attribute temporarily.
- Moves `audit.log` to `audit.log.1`.
- Creates a new audit log.
- Reapplies the append-only attribute.

The gateway service writes its output directly to this audit log.

### Persistent journal

[`config/gateway/journald.conf.d/99-gateway-persistent.conf`](../config/gateway/journald.conf.d/99-gateway-persistent.conf)
sets:

```ini
[Journal]
Storage=persistent
```

This is intended to preserve SSH and Mosquitto events across reboots when
installed under `/etc/systemd/journald.conf.d/`.

### Static status page

[`gateway_status_page.sh`](../gateway/shell_scripts/gateway_status_page.sh):

- Shows whether `gateway.service` is currently running.
- Shows the latest output from the health-check service.
- Finds the latest valid `pico STAT` entry.
- Includes the last 50 audit-log lines.
- Escapes log content for HTML.
- Writes `/var/www/html/index.html` atomically.

The page is refreshed every five seconds by:

- `gateway_status_page.service`
- `gateway_status_page.timer`

It is intended to be served by lighttpd. Lighttpd installation and local
network firewall restrictions still need to be performed and verified.

## Local validation already performed

The implementation has been checked locally for:

- Python syntax compilation.
- Gateway source parsing.
- Valid checksum acceptance.
- Invalid checksum rejection.
- Generated heartbeat checksum.
- Status JSON conversion.
- Valid relay-command acceptance.
- Invalid relay value rejection.
- Boolean relay value rejection.

## Remaining deployment sequence

On the Pi:

```sh
sudo ./gateway/setup_pi.sh
```

If needed, install the web server separately:

```sh
sudo apt install lighttpd
sudo systemctl enable --now lighttpd
```

Then verify:

```sh
sudo systemctl status gateway.service
sudo tail -f /var/log/gateway/audit.log
mosquitto_sub -h localhost -t 'site/#' -v
```

Finally, test the laptop command path, log rotation, append-only behavior,
journald persistence, and the status page before committing and tagging the
unencrypted baseline as `v0.1-working-unencrypted`.
