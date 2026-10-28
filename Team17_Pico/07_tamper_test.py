# 07 - Both tamper sensors together, with the local alarm.
# Needs the wiring from README steps 02, 03, 04 and 05. Nothing new.
# Door open OR light above threshold -> red LED + buzzer. Otherwise green.
from machine import Pin, ADC, PWM
import time

LIGHT_THRESHOLD_PCT = 40   # replace with the value from 04_ldr_calibrate.py
DEBOUNCE_MS = 50

door = Pin(2, Pin.IN)
ldr = ADC(26)
buzzer = PWM(Pin(15))
buzzer.duty_u16(0)
green = Pin(16, Pin.OUT, value=0)
amber = Pin(17, Pin.OUT, value=0)
red = Pin(18, Pin.OUT, value=0)

stable = door.value()
last_raw = stable
changed_at = time.ticks_ms()
alarm = None

try:
    while True:
        now = time.ticks_ms()
        raw = door.value()
        if raw != last_raw:
            last_raw = raw
            changed_at = now
        elif raw != stable and time.ticks_diff(now, changed_at) >= DEBOUNCE_MS:
            stable = raw

        light = ldr.read_u16() * 100 // 65535
        door_open = stable == 1
        too_bright = light > LIGHT_THRESHOLD_PCT
        new_alarm = door_open or too_bright

        if new_alarm != alarm:
            alarm = new_alarm
            if alarm:
                reason = "DOOR+LIGHT" if (door_open and too_bright) else ("DOOR" if door_open else "LIGHT")
                print("ALARM:", reason, "| light", light, "%")
                green.off()
                red.on()
                buzzer.freq(2000)
                buzzer.duty_u16(32768)
            else:
                print("Clear | light", light, "%")
                red.off()
                green.on()
                buzzer.duty_u16(0)
        time.sleep_ms(10)
finally:
    buzzer.duty_u16(0)
    for led in (green, amber, red):
        led.off()
