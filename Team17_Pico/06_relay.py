# 06 - Relay module (HW-482) and the solenoid lock.
# Wiring (README step 06):
#   relay S -> GP14 (pin 19)   relay + -> XL4015 OUT+ (5.0 V)   relay - -> ground (b30)
#   lock side: 12 V adapter + -> relay COM, relay NO -> solenoid, solenoid -> 12 V -
#              plus a diode across the solenoid (see README).
# Never power the relay or the solenoid from the Pico.
#
# The HW-482 switches on when S is HIGH, so RELAY_ACTIVE_LOW = False.
# The relay is on for 1 s each time: a small solenoid gets hot if left on.
from machine import Pin
import time

RELAY_ACTIVE_LOW = False

OFF_LEVEL = 1 if RELAY_ACTIVE_LOW else 0
relay = Pin(14, Pin.OUT, value=OFF_LEVEL)   # start OFF, even for one instant


def set_relay(on):
    if RELAY_ACTIVE_LOW:
        relay.value(0 if on else 1)
    else:
        relay.value(1 if on else 0)


try:
    for i in range(3):
        print("Relay ON  (lock open)")
        set_relay(True)
        time.sleep(1)
        print("Relay OFF (lock closed)")
        set_relay(False)
        time.sleep(2)
    print("Relay test finished")
finally:
    set_relay(False)
