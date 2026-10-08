# 09 - Link tester. Runs on the COMPUTER (laptop or the Pi), not on the Pico.
#
# It plays the part of the gateway: sends a heartbeat every second,
# shows what the Pico reports, and lets you send good and bad commands
# to prove the Pico checks everything it receives.
#
# Needs Python 3 and pyserial:   pip install pyserial
#   (in Thonny: Run > Configure interpreter > "Local Python 3",
#    then Tools > Manage packages > pyserial)
#
# Which port?
#   Laptop + Pico over USB (08_main.py with LINK = "USB"):
#       Windows: COM3, COM4 ... (Thonny shows it bottom-right)
#       Mac:     /dev/tty.usbmodem...      Linux: /dev/ttyACM0
#       Close Thonny's connection to the Pico first (Stop), or the port is busy.
#   Pi + Pico over the GPIO wires (08_main.py with LINK = "UART"):
#       /dev/serial0
#
# Start it:   python3 09_link_tester.py COM4
#             python3 09_link_tester.py /dev/serial0

import sys
import threading
import time

try:
    import serial
except ImportError:
    print("pyserial is missing. Install it with:  pip install pyserial")
    raise SystemExit(1)

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/serial0"
BAUD = 9600            # must match UART_BAUD in 08_main.py (ignored over USB)
HEARTBEAT_EVERY = 1.0  # seconds

HELP = """
Type a command and press Enter:
  on       relay ON             off      relay OFF
  stop     stop the heartbeat (the Pico should go to SAFE after 5 s)
  start    start the heartbeat again
  netdown  heartbeat says the network is down (amber LED)
  netup    heartbeat says the network is fine again
  bad      send a command with a wrong checksum   (expect REJECT,CHECKSUM)
  value    send RELAY=7                            (expect REJECT,VALUE)
  unknown  send a message type the Pico doesn't know (expect REJECT,UNKNOWN)
  long     send a far too long line                (expect REJECT,TOO_LONG)
  junk     send a line that isn't a message at all (expect REJECT,FORMAT)
  quiet    hide the once-a-second STAT lines      loud   show them again
  help     this list                               quit   leave
"""


def checksum(body):
    x = 0
    for ch in body:
        x ^= ord(ch)
    return x


def frame(body):
    return "$%s*%02X" % (body, checksum(body))


def check(line):
    """Returns the fields of a good message, or None if it is damaged."""
    if not line.startswith("$"):
        return None
    star = line.rfind("*")
    if star < 2 or len(line) - star != 3:
        return None
    body = line[1:star]
    try:
        if int(line[star + 1:], 16) != checksum(body):
            return None
    except ValueError:
        return None
    return body.split(",")


class Tester:
    def __init__(self, port):
        self.port = serial.Serial(port, BAUD, timeout=0.1, write_timeout=1)
        self.lock = threading.Lock()        # one print at a time
        self.write_lock = threading.Lock()  # one message at a time on the wire
        self.seq = 0
        self.heartbeat = True
        self.net = "OK"
        self.show_stat = True
        self.running = True
        self.expected = None   # next sequence number we expect from the Pico
        self.lost = 0
        self.damaged = 0

    def say(self, text):
        with self.lock:
            print(text)

    def send_raw(self, text):
        with self.write_lock:
            self.port.write((text + "\n").encode("ascii"))

    def next_seq(self):
        with self.write_lock:
            seq = self.seq
            self.seq = (self.seq + 1) % 65536
            return seq

    def send(self, body_without_seq):
        """body_without_seq like 'CMD,{},RELAY=1' - the {} becomes our counter."""
        body = body_without_seq.format(self.next_seq())
        self.send_raw(frame(body))
        return body

    # -- background jobs
    def heartbeat_loop(self):
        while self.running:
            if self.heartbeat:
                try:
                    self.send("HB,{},NET=" + self.net)
                except serial.SerialException as e:
                    self.say("!! cannot write to the port: %s" % e)
                    self.running = False
            time.sleep(HEARTBEAT_EVERY)

    def read_loop(self):
        buf = b""
        while self.running:
            try:
                data = self.port.read(256)
            except serial.SerialException as e:
                self.say("!! cannot read from the port: %s" % e)
                self.running = False
                return
            if not data:
                continue
            buf += data
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                line = raw.decode("ascii", "replace").strip()
                if line:
                    self.handle(line)

    def handle(self, line):
        if line.startswith("#"):              # the Pico talking to people
            self.say("   pico says: " + line[1:].strip())
            return
        if not line.startswith("$"):
            self.say("   (not a message) " + line)
            return
        fields = check(line)
        if fields is None:
            self.damaged += 1
            self.say("!! DAMAGED message (bad checksum or format): " + line)
            return
        kind = fields[0]
        try:
            seq = int(fields[1])
        except (IndexError, ValueError):
            self.say("!! message without a counter: " + line)
            return
        if kind == "ACK":                      # carries OUR counter, not the Pico's
            self.say(">> ANSWER: " + ",".join(fields[2:]) + "   (to our message #%d)" % seq)
            return
        if self.expected is not None and seq != self.expected:
            missing = (seq - self.expected) % 65536
            self.lost += missing
            self.say("!! %d message(s) missing before #%d (total missing: %d)"
                     % (missing, seq, self.lost))
        self.expected = (seq + 1) % 65536

        if kind == "STAT":
            if self.show_stat:
                self.say("   " + "  ".join(fields[2:]))
        elif kind == "ALRM":
            self.say("** ALARM: " + ",".join(fields[2:]))
        elif kind == "BOOT":
            self.say("** Pico (re)started: " + ",".join(fields[2:]))
            self.expected = (seq + 1) % 65536
        else:
            self.say("   " + line)

    # -- keyboard
    def command(self, word):
        if word == "on":
            self.say("<< " + self.send("CMD,{},RELAY=1"))
        elif word == "off":
            self.say("<< " + self.send("CMD,{},RELAY=0"))
        elif word == "stop":
            self.heartbeat = False
            self.say("<< heartbeat STOPPED - watch the Pico go to SAFE in about 5 s")
        elif word == "start":
            self.heartbeat = True
            self.say("<< heartbeat running again")
        elif word == "netdown":
            self.net = "DOWN"
            self.say("<< heartbeat now says NET=DOWN")
        elif word == "netup":
            self.net = "OK"
            self.say("<< heartbeat now says NET=OK")
        elif word == "bad":
            body = "CMD,%d,RELAY=1" % self.next_seq()
            wrong = (checksum(body) ^ 0x55)
            text = "$%s*%02X" % (body, wrong)
            self.send_raw(text)
            self.say("<< " + text + "   (checksum deliberately wrong)")
        elif word == "value":
            self.say("<< " + self.send("CMD,{},RELAY=7"))
        elif word == "unknown":
            self.say("<< " + self.send("FIRE,{},NOW=1"))
        elif word == "long":
            self.send_raw("$" + "A" * 200)
            self.say("<< a 201-character line")
        elif word == "junk":
            self.send_raw("hello pico")
            self.say("<< hello pico")
        elif word == "quiet":
            self.show_stat = False
        elif word == "loud":
            self.show_stat = True
        elif word == "help":
            self.say(HELP)
        elif word:
            self.say("?? unknown command - type help")

    def run(self):
        threading.Thread(target=self.read_loop, daemon=True).start()
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        self.say("Connected to %s. Heartbeat every %.0f s." % (self.port.port, HEARTBEAT_EVERY))
        self.say(HELP)
        try:
            while self.running:
                word = input().strip().lower()
                if word in ("quit", "exit", "q"):
                    break
                self.command(word)
        except (KeyboardInterrupt, EOFError):
            pass
        self.running = False
        time.sleep(0.2)
        self.port.close()
        self.say("Closed. Damaged messages: %d, missing messages: %d" % (self.damaged, self.lost))


if __name__ == "__main__":
    try:
        Tester(PORT).run()
    except serial.SerialException as e:
        print("Cannot open %s: %s" % (PORT, e))
        print("Check the port name, that the cable is in, and that Thonny is not holding the port.")
