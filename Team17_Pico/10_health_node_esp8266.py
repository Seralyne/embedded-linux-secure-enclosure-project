# 10 - Wi-Fi health node. Runs on the ESP8266 Feather HUZZAH (MicroPython), not the Pico.
#
# Every 10 seconds it sends its own health to the Pi's MQTT broker:
#   uptime, Wi-Fi signal (RSSI), free memory, how many times it reconnected.
# It has no sensor and NO wire to the Pico or the Pi - it is the separate,
# non-critical Wi-Fi zone. If someone takes it over, it can't reach the controller.
#
# Wiring: none. It sits on its own small breadboard and gets power from USB.
#
# Before you run it:
#   1. Flash MicroPython for ESP8266 with Thonny (bottom-right corner >
#      Configure interpreter > MicroPython (ESP8266) > Install or update MicroPython).
#   2. Copy node_config_example.py to node_config.py, fill in Wi-Fi + broker,
#      and save node_config.py ON THE BOARD. Keep it out of git (passwords).
#   3. Save this file on the board as main.py so it starts at power-on.
#
# Watch it on the Pi:  mosquitto_sub -t 'site/node-01/health' -v
#
# This version uses plain MQTT (port 1883), the same as the Phase 8 system.
# TLS for this node is a later step (build guide, Phase 10).

import gc
import json
import time

import machine
import network
from umqtt.simple import MQTTClient

try:
    import node_config as cfg
except ImportError:
    print("node_config.py is missing on the board - see the top of this file.")
    raise

TOPIC = b"site/node-01/health"
CLIENT_ID = b"node-01"
PUBLISH_EVERY_MS = 10000
RETRY_EVERY_S = 5

# Blue LED next to the antenna, GPIO2. It is "active low": 0 = on.
led = machine.Pin(2, machine.Pin.OUT, value=1)

# The ESP8266 MicroPython firmware switches on its own Wi-Fi access point
# at first boot. We don't need it, and an open door is an attack surface.
network.WLAN(network.AP_IF).active(False)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

uptime_ms = 0          # added up step by step, so it never wraps round
last_tick = time.ticks_ms()
reconnects = 0


def blink(ms=50):
    led.value(0)
    time.sleep_ms(ms)
    led.value(1)


def wifi_up():
    if wlan.isconnected():
        return
    print("Wi-Fi: connecting to", cfg.WIFI_SSID)
    wlan.connect(cfg.WIFI_SSID, cfg.WIFI_PASSWORD)
    for i in range(40):                     # up to 20 s
        if wlan.isconnected():
            break
        time.sleep_ms(500)
    if not wlan.isconnected():
        raise OSError("Wi-Fi did not connect")
    print("Wi-Fi: connected, IP", wlan.ifconfig()[0])


def mqtt_up():
    client = MQTTClient(CLIENT_ID, cfg.BROKER, port=cfg.BROKER_PORT, keepalive=30)
    # If the node dies or loses Wi-Fi, the broker announces it for us.
    client.set_last_will(TOPIC, b'{"node":"node-01","online":false}', retain=True)
    client.connect()
    print("MQTT: connected to", cfg.BROKER)
    return client


def tick():
    global uptime_ms, last_tick
    now = time.ticks_ms()
    uptime_ms += time.ticks_diff(now, last_tick)
    last_tick = now


def health():
    return json.dumps({
        "node": "node-01",
        "online": True,
        "uptime_s": uptime_ms // 1000,
        "rssi": wlan.status("rssi"),
        "free_heap": gc.mem_free(),
        "reconnects": reconnects,
    })


def run():
    global reconnects
    client = None
    first = True
    while True:
        try:
            if client is None:
                wifi_up()
                client = mqtt_up()
                if not first:
                    reconnects += 1
                first = False
            gc.collect()
            tick()
            msg = health()
            client.publish(TOPIC, msg.encode(), retain=True)
            print("sent", msg)
            blink()
            time.sleep_ms(PUBLISH_EVERY_MS)
        except OSError as e:
            # Wi-Fi or broker gone: drop the connection, wait, try again.
            print("lost connection:", e, "- retrying in", RETRY_EVERY_S, "s")
            try:
                if client:
                    client.sock.close()
            except Exception:
                pass
            client = None
            time.sleep(RETRY_EVERY_S)
            tick()


run()
