# 02 - The three status LEDs.
# Wiring: README step 02. Each LED has its own 330 ohm resistor in series.
#   green GP16 (pin 21), amber GP17 (pin 22), red GP18 (pin 24)
# If one LED stays dark, turn it round: the long leg is +.
from machine import Pin
import time

green = Pin(16, Pin.OUT, value=0)
amber = Pin(17, Pin.OUT, value=0)
red = Pin(18, Pin.OUT, value=0)
leds = [("green", green), ("amber", amber), ("red", red)]

try:
    for name, led in leds:
        print("Now:", name)
        led.on()
        time.sleep(1)
        led.off()
    print("All three together")
    for name, led in leds:
        led.on()
    time.sleep(1)
    print("LED test finished")
finally:
    for name, led in leds:
        led.off()
