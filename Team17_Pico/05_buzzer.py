# 05 - Passive buzzer.
# Wiring (README step 05): buzzer + to GP15 (pin 20), buzzer - to ground.
# A passive buzzer needs a tone (PWM), not just "on".
from machine import Pin, PWM
import time

buzzer = PWM(Pin(15))
buzzer.duty_u16(0)


def beep(ms, freq=2000):
    buzzer.freq(freq)
    buzzer.duty_u16(32768)   # 50 % on, 50 % off = loudest tone
    time.sleep_ms(ms)
    buzzer.duty_u16(0)


try:
    for i in range(3):
        beep(200)
        time.sleep_ms(200)
    print("Buzzer test finished")
finally:
    buzzer.duty_u16(0)
    buzzer.deinit()
