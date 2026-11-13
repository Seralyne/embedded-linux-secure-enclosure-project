import json
import logging
import os
import sys
import time

import paho.mqtt.client as mqtt
import serial

SERIAL_PORT = os.environ.get('GATEWAY_SERIAL_PORT', '/dev/pts/3')
BAUDRATE = 9600
MQTT_HOST = 'localhost'
MQTT_PORT = 1883
STATUS_TOPIC = 'site/gateway-01/status'
ALARM_TOPIC = 'site/gateway-01/alarm'
COMMAND_TOPIC = 'site/gateway-01/cmd'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z',
    stream=sys.stdout,
)
logger = logging.getLogger('gateway')


def audit(source: str, event: str, detail: str) -> None:
    logger.info('%s %s %s', source, event, detail)


def verify_checksum(line: str) -> bool:
    """Validate a line matching the Pico protocol's checksum format."""
    if not line.startswith('$') or '*' not in line:
        return False
    try:
        payload, received_checksum = line[1:].split('*', 1)
        if len(received_checksum) != 2:
            return False
        calculated = 0
        for char in payload:
            calculated ^= ord(char)
        return f'{calculated:02X}' == received_checksum.upper()
    except ValueError:
        return False


def make_message(body: str) -> str:
    checksum = 0
    for char in body:
        checksum ^= ord(char)
    return f'${body}*{checksum:02X}\n'


def parse_pico_message(line: str) -> tuple[str, list[str]] | None:
    if not verify_checksum(line):
        return None
    payload = line[1:].split('*', 1)[0]
    fields = payload.split(',')
    if len(fields) < 2:
        return None
    return fields[0], fields[1:]


def status_json(fields: list[str]) -> str | None:
    if len(fields) != 5:
        return None
    try:
        result: dict[str, object] = {
            'type': 'STAT',
            'counter': int(fields[0]),
        }
        for field in fields[1:]:
            key, value = field.split('=', 1)
            if key in ('DOOR', 'LIGHT', 'RELAY'):
                result[key.lower()] = int(value)
            elif key == 'STATE':
                result['state'] = value
            else:
                return None
        if not {'door', 'light', 'relay', 'state'} <= result.keys():
            return None
        return json.dumps(result, separators=(',', ':'))
    except (TypeError, ValueError):
        return None


def alarm_json(fields: list[str]) -> str | None:
    if len(fields) != 2:
        return None
    try:
        return json.dumps({
            'type': 'ALRM',
            'counter': int(fields[0]),
            'reason': fields[1],
        }, separators=(',', ':'))
    except ValueError:
        return None


class Counter:
    def __init__(self) -> None:
        self.value = 0

    def next(self) -> int:
        current = self.value
        self.value = (self.value + 1) % 65536
        return current


def command_body(payload: bytes, counter: Counter) -> str | None:
    try:
        command = json.loads(payload.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(command, dict) or set(command) != {'relay'}:
        return None
    relay = command['relay']
    if type(relay) is not int or relay not in (0, 1):
        return None
    return f'CMD,{counter.next()},RELAY={relay}'


def main() -> None:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1, write_timeout=1)
    counter = Counter()
    client = mqtt.Client()

    def on_connect(
        client: mqtt.Client,
        userdata: object,
        flags: dict,
        reason_code: int,
        properties: object = None,
    ) -> None:
        if reason_code != 0:
            audit('mqtt', 'CONNECT_FAILED', f'code={reason_code}')
            return
        client.subscribe(COMMAND_TOPIC)
        audit('mqtt', 'CONNECTED', f'subscribed={COMMAND_TOPIC}')

    def on_command(
        client: mqtt.Client,
        userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        body = command_body(message.payload, counter)
        if body is None:
            audit('mqtt', 'CMD_REJECTED', f'topic={message.topic}')
            return
        ser.write(make_message(body).encode('ascii'))
        ser.flush()
        audit('mqtt', 'CMD_ACCEPTED', f'topic={message.topic} body={body}')

    client.on_connect = on_connect
    client.on_message = on_command
    try:
        client.connect(MQTT_HOST, MQTT_PORT)
    except OSError as exc:
        audit('mqtt', 'CONNECT_FAILED', f'error={exc}')
        ser.close()
        return
    client.loop_start()
    last_hb = 0.0
    audit('gateway', 'STARTED', f'serial={SERIAL_PORT}')

    try:
        while True:
            raw_line = ser.readline().decode('utf-8', errors='ignore').strip()
            if raw_line:
                parsed = parse_pico_message(raw_line)
                if parsed is None:
                    audit('pico', 'MESSAGE_REJECTED', raw_line)
                else:
                    kind, fields = parsed
                    if kind == 'STAT':
                        payload = status_json(fields)
                        if payload is None:
                            audit('pico', 'STAT_REJECTED', raw_line)
                        else:
                            client.publish(STATUS_TOPIC, payload)
                            audit('pico', 'STAT', raw_line)
                    elif kind == 'ALRM':
                        payload = alarm_json(fields)
                        if payload is None:
                            audit('pico', 'ALRM_REJECTED', raw_line)
                        else:
                            client.publish(ALARM_TOPIC, payload)
                            audit('pico', 'ALARM', raw_line)

            if time.time() - last_hb >= 1.0:
                ser.write(make_message(
                    f'HB,{counter.next()},NET=OK',
                ).encode('ascii'))
                ser.flush()
                audit('gateway', 'HEARTBEAT_SENT', 'NET=OK')
                last_hb = time.time()
    except KeyboardInterrupt:
        audit('gateway', 'STOPPED', 'keyboard interrupt')
    finally:
        client.loop_stop()
        client.disconnect()
        ser.close()


if __name__ == '__main__':
    main()
