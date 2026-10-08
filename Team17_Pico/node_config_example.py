# Copy this file to node_config.py, fill it in, and save node_config.py
# on the ESP8266 (in Thonny: File > Save as > MicroPython device).
# node_config.py holds the Wi-Fi password: keep it OUT of git
# (add "node_config.py" to .gitignore).

WIFI_SSID = "your-wifi-name"
WIFI_PASSWORD = "your-wifi-password"

BROKER = "192.168.1.50"   # the Pi's IP address (gateway-01). Use the IP, not
                          # gateway-01.local - the ESP8266 can't look up .local names.
BROKER_PORT = 1883        # plain MQTT for now (Phase 8). TLS comes later.
