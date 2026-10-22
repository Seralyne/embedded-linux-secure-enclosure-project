import time
import serial
import sys

SERIAL_PORT = '/dev/pts/3'
BAUDRATE = 9600

def verify_checksum(line: str) -> bool:
    """Validates lines matching format: $msg*CS (e.g., $STAT,OK*3A)"""
    if not line.startswith('$') or '*' not in line:
        return False
    try:
        payload, received_checksum = line[1:].split('*', 1)
        # Calculate NMEA XOR checksum
        calc_cksum = 0
        for char in payload:
            calc_cksum ^= ord(char)
        return f"{calc_cksum:02X}" == received_checksum.upper()
    except ValueError:
        return False

# Open serial port
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
last_hb = time.time()

print(f"Gateway, SERVICE, START, Listening on {SERIAL_PORT}")

try:
    while True:
        # 1. Read incoming data
        raw_line = ser.readline().decode('utf-8', errors='ignore').strip()
        if raw_line:
            if raw_line.startswith('$STAT'):
                if verify_checksum(raw_line):
                    print(f"Pico, RX_STAT, VALID, {raw_line}")
                else:
                    print(f"Pico, RX_STAT, REJECTED, Bad Checksum: {raw_line}")
            else:
                print(f"Pico, RX_UNKNOWN, IGNORED, {raw_line}")

        # 2. Send $HB every second
        if time.time() - last_hb >= 1.0:
            ser.write(b"$HB*5C\n")
            ser.flush()
            last_hb = time.time()

except KeyboardInterrupt:
    print("Gateway, SERVICE, STOP, Terminated by user")
finally:
    ser.close()