# 04 - Light sensor (LDR) reading and calibration.
# Wiring (README step 04): 3.3 V -> LDR -> GP26 (pin 31);  GP26 -> 10k -> AGND (pin 33).
# More light = higher reading.
# Run this with the box built and the lid shut, then open, to get YOUR threshold.
from machine import ADC
import time

ldr = ADC(26)


def percent():
    return ldr.read_u16() * 100 // 65535


def measure(seconds):
    low, high = 100, 0
    end = time.ticks_add(time.ticks_ms(), seconds * 1000)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        p = percent()
        low = min(low, p)
        high = max(high, p)
        time.sleep_ms(50)
    return low, high


print("Live reading for 5 seconds. Cover the LDR and uncover it to see it move.")
for i in range(25):
    print("light:", percent(), "%")
    time.sleep_ms(200)

input("\nClose the lid (or cover the LDR fully) and press Enter...")
dark_low, dark_high = measure(5)
print("Lid shut:   lowest", dark_low, "%  highest", dark_high, "%")

input("Open the lid in normal room light and press Enter...")
light_low, light_high = measure(5)
print("Lid open:   lowest", light_low, "%  highest", light_high, "%")

if light_low > dark_high:
    threshold = (dark_high + light_low) // 2
    print("\nSuggested LIGHT_THRESHOLD_PCT =", threshold)
    print("Put this number in 07_tamper_test.py and 08_main.py.")
    print("Gap between shut and open:", light_low - dark_high, "%")
    if light_low - dark_high < 10:
        print("The gap is small. Try the 4.7k resistor instead of the 10k and run again.")
else:
    print("\nShut and open readings overlap - no safe threshold.")
    print("Check the wiring, block light leaks, or try the 4.7k resistor.")
