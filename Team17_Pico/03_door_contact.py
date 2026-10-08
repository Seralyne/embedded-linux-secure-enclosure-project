# 03 - Door contact with debounce.
# Wiring (README step 03): 10k pull-up from 3.3 V to GP2 (pin 4); contact between GP2 and ground.
# No door contact yet? Two jumpers in d21 and b26: touch the free ends = shut.
#   Door shut (contact closed)       -> GP2 reads 0
#   Door open, OR the wire is cut    -> GP2 reads 1  (alarm - this is on purpose)
from machine import Pin
import time

DEBOUNCE_MS = 50   # value must stay the same this long before we believe it

door = Pin(2, Pin.IN)   # no internal pull needed: the external 10k does the job

stable = door.value()
last_raw = stable
changed_at = time.ticks_ms()
print("Start:", "SHUT" if stable == 0 else "OPEN (or wire cut)")

while True:
    raw = door.value()
    now = time.ticks_ms()
    if raw != last_raw:
        last_raw = raw
        changed_at = now
    elif raw != stable and time.ticks_diff(now, changed_at) >= DEBOUNCE_MS:
        stable = raw
        print("Door:", "SHUT" if stable == 0 else "OPEN (or wire cut)")
    time.sleep_ms(5)
