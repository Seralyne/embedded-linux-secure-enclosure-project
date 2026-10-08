# 01 - Blink the Pico's own LED.
# Proves the cable, MicroPython and Thonny all work. No wiring needed.
# Original Raspberry Pi Pico (RP2040, no Wi-Fi): the on-board LED is GP25.
from machine import Pin
import time

onboard = Pin(25, Pin.OUT, value=0)

try:
    for count in range(5):
        onboard.on()
        time.sleep(0.3)
        onboard.off()
        time.sleep(0.3)
    print("Blink test finished")
finally:
    onboard.off()
