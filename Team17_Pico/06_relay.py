# 06 - Relay module.
# Wiring (README step 06): relay IN to GP14 (pin 19). Relay VCC to its OWN 5 V supply.
#         Relay GND to that supply's ground AND to the Pico's ground.
# Never power the relay from the Pico.
#
# The module has a LOW/HIGH trigger jumper. Set RELAY_ACTIVE_LOW to match it:
#   jumper on H -> RELAY_ACTIVE_LOW = False
#   jumper on L -> RELAY_ACTIVE_LOW = True
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
        print("Relay ON")
        set_relay(True)
        time.sleep(1)
        print("Relay OFF")
        set_relay(False)
        time.sleep(1)
    print("Relay test finished")
finally:
    set_relay(False)
