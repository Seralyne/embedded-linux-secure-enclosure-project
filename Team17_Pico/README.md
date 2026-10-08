# Team 17 — Pico wiring and scripts

The picture `Team17_Wiring_reference.png` shows every part and every wire on the breadboard.
This file says the same thing as a list, step by step, so you can build a little, test it with the matching script, then add the next part.

**How holes are named.** The Pico sits in columns c and h, USB at the top.

- **Beside the Pico** the board doesn't print row numbers. It prints the pin label (TX, RX, G, 2, 3 … on the left; 5V, Vs, G, 3e, 3V … 16 on the right). So these holes are written **column + printed label in brackets**: `a[2]` = column a, in the row printed **2** (that's GP2). `j[3V]` = column j, row printed **3V**.
- The board prints **G** eight times. Each one is named by where it is: `a[G under RX]`, `a[G 9/10]` (between 9 and 10), `a[G 13/14]`, `j[G 18/17]`, `j[G 28/27]`. **The G between 28 and 27 on the right is AGND** (Pico pin 33), not ordinary ground.
- **Below the Pico** the board prints 21–30. These are plain: `a26` = column a, row 26.
- Careful: `j[26]` (beside the Pico, GP26) and `j26` (free row 26) are different holes.

In each row, holes a–e are joined, and holes f–j are joined. Left and right halves are **not** joined. The + / − rails on the sides are not used.

**Before every change:** unplug the Pico's USB cable (and the relay's 5 V supply).

---

## The scripts

| File | Runs on | What it proves | Wiring needed |
|---|---|---|---|
| `01_onboard_blink.py` | Pico | Cable, MicroPython and Thonny work | none |
| `02_status_leds.py` | Pico | Green, amber, red LEDs | step 02 |
| `03_door_contact.py` | Pico | Door shut / open / wire cut | step 03 |
| `04_ldr_calibrate.py` | Pico | Light sensor + finds your threshold | step 04 |
| `05_buzzer.py` | Pico | Buzzer beeps | step 05 |
| `06_relay.py` | Pico | Relay clicks on and off | step 06 |
| `07_tamper_test.py` | Pico | Door or light → red LED + buzzer | steps 02–05 |
| `08_main.py` | Pico (saved as `main.py`) | The real controller | steps 02–06 (+ step 08 for the Pi) |
| `09_link_tester.py` | Laptop or Pi | Pretends to be the gateway, tests 08 | none |
| `10_health_node_esp8266.py` | ESP8266 HUZZAH (saved as `main.py`) | Sends its own health to the Pi over Wi-Fi + MQTT | none (USB power only) |

`PROTOCOL.md` describes the messages between the Pico and the Pi.

---

## Wiring, step by step

### Step 02 — Status LEDs

| What | From | To |
|---|---|---|
| Wire (GP16, green LED) | j[16] | j22 |
| Wire (GP17, amber LED) | i[17] | j23 |
| Wire (GP18, red LED) | i[18] | j25 |
| Wire (ground) | a[G 13/14] | a21 |
| Short wire (ground, links row 21 to row 24) | b21 | b24 |
| 330 Ω resistor | d22 | f22 |
| 330 Ω resistor | d23 | f23 |
| 330 Ω resistor | d25 | f25 |
| Green LED | long leg **c22** | short leg c21 |
| Amber LED | long leg **c23** | short leg c24 |
| Red LED | long leg **a25** | short leg a24 |

The three resistors lie across the centre channel. Rows 21 and 24 (left) are now ground.

### Step 03 — Door contact

| What | From | To |
|---|---|---|
| Wire (GP2) | a[2] | a26 |
| Wire (3.3 V) | j[3V] | j26 |
| 10 kΩ resistor (pull-up) | d26 | f26 |
| Door contact, wire 1 | d21 (ground) | — |
| Door contact, wire 2 | b26 | — |

The door contact has no + or −. Either wire can go in either hole.
**No door contact yet?** Put a jumper in d21 and one in b26. Touch their free ends together = door shut. Pull them apart = door open.

What the script should print: ends touching → `SHUT`. Apart, or one wire pulled out → `OPEN (or wire cut)`. That second case is on purpose: a cut cable must look like an alarm.

### Step 04 — Light sensor (LDR)

| What | From | To |
|---|---|---|
| Wire (GP26) | j[26] | j27 |
| Wire (AGND — analogue ground) | j[G 28/27] | j30 |
| LDR | g26 | g27 |
| 10 kΩ resistor (load) | h27 | h30 |

Needs the 3.3 V wire from step 03 (j[3V] → j26). The LDR has no + or −.
Row 30 **right** is AGND. It is only for the light sensor — don't use it as an ordinary ground.

Run `04_ldr_calibrate.py` with the box closed, then open. It prints a number. Put it in `LIGHT_THRESHOLD_PCT` in `07_tamper_test.py` and `08_main.py`.
If it says the gap is small, swap the 10 kΩ in h27–h30 for the 4.7 kΩ and run it again.

### Step 05 — Buzzer

| What | From | To |
|---|---|---|
| Wire (GP15) | a[15] | a29 |
| Wire (ground) | j[G 18/17] | j29 |
| Buzzer | **+ leg e29** | − leg f29 |

The buzzer sits across the centre channel. The + leg is usually marked on top or is the longer leg.
Its round body covers the middle holes of rows 27–30; that's why nothing else goes there.

### Step 06 — Relay and its own 5 V supply

| What | From | To |
|---|---|---|
| Wire (ground) | a[G 9/10] | a30 |
| Male–female wire (GP14) | a[14] | relay **IN** |
| Male–female wire (ground) | b30 | relay **GND** (DC−) |
| 5 V supply **black / −** | c30 | — |
| 5 V supply **red / +** | relay **VCC** (DC+) directly | — |

- Row 30 left is the meeting point for the grounds: Pico ground (a30, from a[G 9/10]), relay ground (b30), supply ground (c30). Without this shared ground the relay won't react to the Pico.
- The red / + wire of the 5 V supply **never goes on the breadboard**. 5 V on any Pico row can kill the Pico.
- Bare wire from a cut USB cable: twist the strands tight (or solder them to a pin) before pushing into c30.
- The relay has a jumper marked H / L. Jumper on **H** → `RELAY_ACTIVE_LOW = False` (in `06_relay.py` and `08_main.py`). Jumper on **L** → `True`.
- If your relay has screw terminals instead of pins, clamp the wire under the screw instead of using a female end.

### Step 08 — Link to the Raspberry Pi (only when `LINK = "UART"`)

| What | From (Pico) | To (Pi header) |
|---|---|---|
| Male–female wire, Pico TX | a[TX] (GP0) | **pin 10** (RXD) |
| Male–female wire, Pico RX | a[RX] (GP1) | **pin 8** (TXD) |
| Male–female wire, ground | a[G under RX] | **pin 6** (GND) |

TX goes to RX and RX to TX — they cross. Both boards use 3.3 V here, so no level shifter is needed.
The Pico keeps its own USB power. The Pi has its own supply. Only these three wires join them.

### Not on the breadboard — the clock module (DS3231) on the Pi

| DS3231 | Pi header |
|---|---|
| VCC | pin 1 (3.3 V) |
| SDA | pin 3 |
| SCL | pin 5 |
| GND | pin 9 |

Both ends are pins, so these need female–female wires.

### The ESP8266 Feather HUZZAH — no wiring

It sits on its own small breadboard and only needs its USB cable for power. It has **no wire to the Pico or the Pi**. That is on purpose: it is the separate, non-critical Wi-Fi zone, so if someone takes it over they can't reach the controller.

1. Thonny: bottom-right corner → *Configure interpreter* → *MicroPython (ESP8266)* → *Install or update MicroPython*. Pick the HUZZAH's port.
2. Copy `node_config_example.py` to `node_config.py`, fill in the Wi-Fi name, password and the Pi's **IP address** (the ESP8266 can't look up `gateway-01.local`). Save it on the board. Never commit it to git.
3. Open `10_health_node_esp8266.py`, *Save as → MicroPython device* → `main.py`.
4. On the Pi (mosquitto running, Phase 8): `mosquitto_sub -t 'site/node-01/health' -v` → one line every 10 s.

The blue LED near the antenna blinks once per message. If the Wi-Fi or the broker goes away, it retries every 5 s and counts the reconnect. If it dies, the broker sends `{"online":false}` for it (MQTT "last will").
It also switches off the Wi-Fi access point that MicroPython opens by itself on the ESP8266.
If Thonny says `no module named 'umqtt'`: *Tools → Manage packages* → install `micropython-umqtt.simple` onto the board.

### Wire count

About 12 male–male wires on the board (plus the door contact's own two wires) and 5 male–female wires (2 to the relay, 3 to the Pi).

---

## Using Thonny

**First time:** hold the BOOTSEL button on the Pico, plug in USB, let go. In Thonny: click the bottom-right corner → *Configure interpreter* → *MicroPython (Raspberry Pi Pico)* → *Install or update MicroPython*.

**Scripts 01–07:** open the file, press **Run** (F5). It runs straight from the laptop; nothing is saved on the Pico. Press **Stop** to end 03 and 07 (they run until stopped).

**Script 08 (the controller):**
1. Set the values at the top: `LINK`, `LIGHT_THRESHOLD_PCT`, `RELAY_ACTIVE_LOW`.
2. *File → Save as → Raspberry Pi Pico* → name it **`main.py`**. Now it starts by itself whenever the Pico gets power.
3. To try it with the laptop (`LINK = "USB"`): unplug and replug the Pico, **close Thonny** (it holds the port), then on the laptop:
   ```
   pip install pyserial
   python 09_link_tester.py COM4          (Windows — your port number)
   python3 09_link_tester.py /dev/ttyACM0 (Linux)
   ```
4. With the Pi (`LINK = "UART"`): wire step 08, then on the Pi: `python3 09_link_tester.py /dev/serial0`

**What to try with 09:** type `help`. Then `on`, `off`, `bad`, `value`, `unknown`, `long`, `junk`, `netdown`, `netup`, `stop` (wait 5 s — red LED, buzzer, relay off), `on` (refused while SAFE), `start`.
These are tests T1, T4, T5 and T6 from the proposal, and T10 (missing messages) is counted at the bottom when you `quit`.

**Watchdog:** keep `USE_WATCHDOG = False` while developing. When it is `True`, the Pico restarts itself 2 s after the program stops — Thonny's Stop button included — which makes editing awkward. Turn it on only for the final system. To get control back: press Stop several times quickly right after the Pico restarts, then rename `main.py` on the Pico.

**The Pi side, once:** the serial port must be free for our program.
- `sudo raspi-config` → *Interface Options* → *Serial Port* → login shell over serial: **No**; serial port hardware: **Yes**
- add `dtoverlay=disable-bt` to `/boot/firmware/config.txt`, then reboot — this puts `/dev/serial0` on the good UART (pins 8/10)
- your user needs to be in the `dialout` group to open it: `sudo usermod -aG dialout $USER`, then log out and in

---

## If something doesn't work

| Problem | Check |
|---|---|
| LED stays dark | Turned round? Long leg on the resistor side. Is its short leg in a ground row (21 or 24)? |
| Door always says OPEN | The 10 kΩ must be d26–f26 and the 3.3 V wire j[3V]–j26. Is wire 1 in d21? |
| Light reading stuck near 0 or 100 | LDR in g26–g27? 10 kΩ in h27–h30? AGND wire j[G 28/27]–j30? GP26 wire from j[26] (beside the Pico), not j26? |
| Buzzer silent | + leg in e29? A passive buzzer only sounds with PWM — the script does this. |
| Relay LED lights but no click, or nothing at all | 5 V supply plugged in? Shared ground in row 30 left? H/L jumper matches `RELAY_ACTIVE_LOW`? |
| 09 says it cannot open the port | Thonny still open? Wrong port name? On the Pi: `dialout` group, serial console off? |
| 09 shows nothing over UART | TX/RX crossed (a[TX] → Pi pin 10, a[RX] → pin 8)? `LINK = "UART"` saved in main.py? Ground wire a[G under RX] → pin 6? |
| Pico shows ALARM straight away | That's correct if the door contact isn't connected — an open circuit means "door open". |
