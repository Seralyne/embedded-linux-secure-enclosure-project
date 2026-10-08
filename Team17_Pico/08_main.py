# 08 - Team 17 equipment controller (Raspberry Pi Pico, MicroPython)
#
# What it does
#   - reads the door contact and the light sensor (LDR)
#   - switches the relay when the Pi asks, but only after checking the command
#   - sends a status line to the Pi once a second
#   - shows its state on the green / amber / red LEDs, and beeps on alarm
#   - goes to a SAFE state on its own if it stops hearing from the Pi
#
# In Thonny: File > Save as > Raspberry Pi Pico > name it main.py
# so it starts by itself at power-on.
# Message format: see PROTOCOL.md.
#
# Two settings to change before you use it:
#   LINK              "USB"  - talk to a laptop over the USB cable (testing, no Pi)
#                     "UART" - talk to the Pi over GP0/GP1 (the real system)
#   LIGHT_THRESHOLD_PCT  - the number from 04_ldr_calibrate.py

from machine import Pin, ADC, PWM
import machine
import time
import sys

# ---------------------------------------------------------------- settings
LINK = "USB"                 # "USB" or "UART"
UART_BAUD = 9600
LIGHT_THRESHOLD_PCT = 40     # from 04_ldr_calibrate.py
HEARTBEAT_TIMEOUT_MS = 5000  # no heartbeat this long -> SAFE state
STATUS_EVERY_MS = 1000
DEBOUNCE_MS = 50
MAX_LINE = 64                # longer incoming lines are thrown away
RELAY_ACTIVE_LOW = False     # match the relay module's L/H jumper
USE_WATCHDOG = False         # set True for the final system (see README)
WATCHDOG_MS = 2000

# ---------------------------------------------------------------- pins
PIN_DOOR = 2      # pin 4,  10k pull-up to 3.3 V, contact to ground
PIN_RELAY = 14    # pin 19
PIN_BUZZER = 15   # pin 20
PIN_GREEN = 16    # pin 21
PIN_AMBER = 17    # pin 22
PIN_RED = 18      # pin 24
PIN_LDR = 26      # pin 31 (ADC0)


# ---------------------------------------------------------------- protocol
def checksum(body):
    """XOR of every character between '$' and '*'."""
    x = 0
    for ch in body:
        x ^= ord(ch)
    return x


def frame(body):
    """'STAT,1,...' -> '$STAT,1,...*4F'"""
    return "$%s*%02X" % (body, checksum(body))


def parse(line):
    """Check one incoming line. Returns the list of fields,
    or raises ValueError(reason) if the line is not acceptable."""
    if len(line) > MAX_LINE:
        raise ValueError("TOO_LONG")
    for ch in line:
        if ord(ch) < 32 or ord(ch) > 126:
            raise ValueError("FORMAT")
    if not line.startswith("$"):
        raise ValueError("FORMAT")
    star = line.rfind("*")
    if star < 2 or len(line) - star != 3:
        raise ValueError("FORMAT")
    body = line[1:star]
    try:
        received = int(line[star + 1:], 16)
    except ValueError:
        raise ValueError("FORMAT")
    if received != checksum(body):
        raise ValueError("CHECKSUM")
    return body.split(",")


def parse_seq(text):
    if not text or len(text) > 5:
        raise ValueError("FORMAT")
    for ch in text:
        if ch < "0" or ch > "9":
            raise ValueError("FORMAT")
    value = int(text)
    if value > 65535:
        raise ValueError("FORMAT")
    return value


# ---------------------------------------------------------------- links
class UsbLink:
    """Talk over the USB cable (for testing from a laptop)."""

    def __init__(self):
        import select
        self.poll = select.poll()
        self.poll.register(sys.stdin, select.POLLIN)
        self.buf = ""
        self.overflow = False

    def send(self, text):
        print(text)

    def read_lines(self):
        lines = []
        while self.poll.poll(0):
            ch = sys.stdin.read(1)
            if not ch:
                break
            if ch == "\n" or ch == "\r":
                if self.overflow:
                    lines.append(None)          # None = line was too long
                elif self.buf:
                    lines.append(self.buf)
                self.buf = ""
                self.overflow = False
            elif len(self.buf) < MAX_LINE:
                self.buf += ch
            else:
                self.overflow = True
        return lines


class UartLink:
    """Talk to the Pi over GP0 (TX) and GP1 (RX)."""

    def __init__(self):
        from machine import UART
        self.uart = UART(0, baudrate=UART_BAUD, tx=Pin(0), rx=Pin(1))
        self.buf = bytearray()
        self.overflow = False

    def send(self, text):
        self.uart.write(text + "\n")

    def read_lines(self):
        lines = []
        data = self.uart.read()
        if not data:
            return lines
        for b in data:
            if b == 10 or b == 13:
                if self.overflow:
                    lines.append(None)
                elif self.buf:
                    try:
                        lines.append(bytes(self.buf).decode())
                    except Exception:
                        lines.append("\x00")    # not text -> rejected as FORMAT
                self.buf = bytearray()
                self.overflow = False
            elif len(self.buf) < MAX_LINE:
                self.buf.append(b)
            else:
                self.overflow = True
        return lines


# ---------------------------------------------------------------- controller
class Controller:
    def __init__(self, link, now):
        self.link = link
        self.door = Pin(PIN_DOOR, Pin.IN)          # external 10k pull-up
        self.ldr = ADC(PIN_LDR)
        off = 1 if RELAY_ACTIVE_LOW else 0
        self.relay_pin = Pin(PIN_RELAY, Pin.OUT, value=off)
        self.buzzer = PWM(Pin(PIN_BUZZER))
        self.buzzer.freq(2000)
        self.buzzer.duty_u16(0)
        self.green = Pin(PIN_GREEN, Pin.OUT, value=0)
        self.amber = Pin(PIN_AMBER, Pin.OUT, value=0)
        self.red = Pin(PIN_RED, Pin.OUT, value=0)

        self.seq = 0                 # our outgoing message counter
        self.relay_on = False
        self.door_stable = self.door.value()
        self.door_raw = self.door_stable
        self.door_changed_at = now
        self.light = self.read_light()
        self.last_hb = None          # time of last good heartbeat, None = never
        self.net_ok = True
        self.safe = False
        self.alarm_reasons = []
        self.state = "START"
        self.last_status = now
        self.beep_on = False
        self.beep_changed = now

    # -- output helpers
    def send(self, body):
        # our own messages (BOOT, STAT, ALRM) carry our counter, so the Pi
        # can spot a missing one; the counter moves on after each of them
        self.link.send(frame(body))
        self.seq = (self.seq + 1) % 65536

    def reply(self, body):
        # answers (ACK) carry the Pi's counter instead, so they don't move ours
        self.link.send(frame(body))

    def next_seq(self):
        return self.seq

    def log(self, text):
        # Lines starting with '#' are for people; the gateway ignores them.
        print("# " + text)

    def set_relay(self, on):
        self.relay_on = on
        if RELAY_ACTIVE_LOW:
            self.relay_pin.value(0 if on else 1)
        else:
            self.relay_pin.value(1 if on else 0)

    # -- inputs
    def read_light(self):
        total = 0
        for i in range(4):
            total += self.ldr.read_u16()
        return total * 100 // (4 * 65535)

    def sample_door(self, now):
        raw = self.door.value()
        if raw != self.door_raw:
            self.door_raw = raw
            self.door_changed_at = now
        elif raw != self.door_stable and time.ticks_diff(now, self.door_changed_at) >= DEBOUNCE_MS:
            self.door_stable = raw

    # -- incoming messages
    def reject(self, seq, reason):
        self.reply("ACK,%d,REJECT,%s" % (seq, reason))
        self.log("rejected: " + reason)

    def handle_line(self, line, now):
        if line is None:
            self.reject(0, "TOO_LONG")
            return
        try:
            fields = parse(line)
        except ValueError as e:
            self.reject(0, e.args[0])
            return
        kind = fields[0]
        try:
            seq = parse_seq(fields[1]) if len(fields) > 1 else None
        except ValueError:
            self.reject(0, "FORMAT")
            return
        if seq is None or len(fields) != 3:
            self.reject(seq or 0, "FORMAT")
            return
        value = fields[2]

        if kind == "HB":
            if value == "NET=OK":
                self.net_ok = True
            elif value == "NET=DOWN":
                self.net_ok = False
            else:
                self.reject(seq, "VALUE")
                return
            self.last_hb = now
        elif kind == "CMD":
            if value == "RELAY=1":
                if self.safe:
                    self.reject(seq, "STATE")   # no commands while the link is lost
                    return
                self.set_relay(True)
            elif value == "RELAY=0":
                self.set_relay(False)           # switching OFF is always allowed
            else:
                self.reject(seq, "VALUE")
                return
            self.reply("ACK,%d,OK" % seq)
            self.log("relay " + ("ON" if self.relay_on else "OFF"))
        else:
            self.reject(seq, "UNKNOWN")

    # -- state
    def update(self, now):
        # link health
        if self.last_hb is None:
            link = "START"
        elif time.ticks_diff(now, self.last_hb) > HEARTBEAT_TIMEOUT_MS:
            link = "LOST"
        else:
            link = "OK" if self.net_ok else "NETDOWN"

        if link == "LOST" and not self.safe:
            self.safe = True
            self.set_relay(False)
            self.send("ALRM,%d,LINK" % self.next_seq())
            self.log("heartbeat lost -> SAFE state, relay OFF")
        elif link in ("OK", "NETDOWN") and self.safe:
            self.safe = False
            self.log("heartbeat back -> leaving SAFE state (relay stays OFF)")

        # tamper
        reasons = []
        if self.door_stable == 1:
            reasons.append("DOOR")
        if self.light > LIGHT_THRESHOLD_PCT:
            reasons.append("LIGHT")
        for r in reasons:
            if r not in self.alarm_reasons:
                self.send("ALRM,%d,%s" % (self.next_seq(), r))
                self.log("ALARM " + r)
        if self.alarm_reasons and not reasons:
            self.send("ALRM,%d,CLEAR" % self.next_seq())
            self.log("alarm cleared")
        self.alarm_reasons = reasons

        # overall state, most serious first
        if self.safe:
            self.state = "SAFE"
        elif reasons:
            self.state = "ALARM"
        elif link == "START":
            self.state = "START"
        elif link == "NETDOWN":
            self.state = "NETDOWN"
        else:
            self.state = "OK"

    def show(self, now):
        s = self.state
        self.green.value(1 if s == "OK" else 0)
        self.amber.value(1 if s in ("START", "NETDOWN") else 0)
        self.red.value(1 if s in ("ALARM", "SAFE") else 0)
        # buzzer: 300 ms on, 300 ms off while in ALARM or SAFE
        if s in ("ALARM", "SAFE"):
            if time.ticks_diff(now, self.beep_changed) >= 300:
                self.beep_on = not self.beep_on
                self.beep_changed = now
            self.buzzer.duty_u16(32768 if self.beep_on else 0)
        else:
            self.beep_on = False
            self.buzzer.duty_u16(0)

    def status(self):
        self.send("STAT,%d,DOOR=%d,LIGHT=%03d,RELAY=%d,STATE=%s" % (
            self.next_seq(), self.door_stable, self.light,
            1 if self.relay_on else 0, self.state))

    def step(self, now):
        for line in self.link.read_lines():
            self.handle_line(line, now)
        self.sample_door(now)
        self.light = self.read_light()
        self.update(now)
        self.show(now)
        if time.ticks_diff(now, self.last_status) >= STATUS_EVERY_MS:
            self.last_status = now
            self.status()

    def all_off(self):
        self.set_relay(False)
        self.buzzer.duty_u16(0)
        for led in (self.green, self.amber, self.red):
            led.value(0)


# ---------------------------------------------------------------- start
def reset_cause_text():
    try:
        cause = machine.reset_cause()
    except Exception:
        return "UNKNOWN"
    if cause == getattr(machine, "WDT_RESET", -1):
        return "WDT"
    if cause == getattr(machine, "PWRON_RESET", -2):
        return "POWER"
    return "OTHER"


def run():
    link = UartLink() if LINK == "UART" else UsbLink()
    c = Controller(link, time.ticks_ms())
    c.send("BOOT,%d,CAUSE=%s" % (c.next_seq(), reset_cause_text()))
    c.log("controller started, link=" + LINK)
    wdt = machine.WDT(timeout=WATCHDOG_MS) if USE_WATCHDOG else None
    try:
        while True:
            c.step(time.ticks_ms())
            if wdt:
                wdt.feed()
            time.sleep_ms(5)
    finally:
        c.all_off()


if __name__ == "__main__":
    run()
