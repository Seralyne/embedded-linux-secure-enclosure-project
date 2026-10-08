# Pico ↔ Pi messages (Team 17)

One message = one line of plain text, ended by a newline.

```
$TYPE,counter,data*CS
```

| Part | Meaning |
|---|---|
| `$` | start of a message |
| `TYPE` | what kind of message (table below) |
| `counter` | 0 to 65535, goes up by one each message, then starts again at 0 |
| `data` | one or more fields, separated by commas |
| `*CS` | checksum: XOR of every character between `$` and `*`, written as 2 hex digits (capital letters) |

Line speed: 9600 baud, 8N1. Lines longer than 64 characters are thrown away.
Lines that start with `#` are notes for people (the Pico's log). Programs ignore them.

All the examples below have **real** checksums, so they can be pasted into a test.

## Pi → Pico

| Message | Example | What the Pico does |
|---|---|---|
| Heartbeat, network fine | `$HB,41,NET=OK*69` | Sent every second. Green LED. |
| Heartbeat, network down | `$HB,42,NET=DOWN*7C` | The Pi has lost its own network. Amber LED. The Pico keeps working. |
| Relay on | `$CMD,43,RELAY=1*02` | Switches the relay on, answers `ACK`. Refused while in SAFE state. |
| Relay off | `$CMD,44,RELAY=0*04` | Switches the relay off. Always allowed, even in SAFE state. |

## Pico → Pi

| Message | Example | When |
|---|---|---|
| Started | `$BOOT,0,CAUSE=POWER*05` | Once, at start. CAUSE = POWER, WDT (watchdog restarted it) or OTHER. |
| Status | `$STAT,120,DOOR=0,LIGHT=012,RELAY=1,STATE=OK*67` | Every second. DOOR 0 = shut, 1 = open or wire cut. LIGHT 000–100 %. |
| Alarm | `$ALRM,121,DOOR*36` | Door opened (or wire cut). |
| | `$ALRM,122,LIGHT*7D` | Light inside the box above the threshold. |
| | `$ALRM,123,LINK*22` | No heartbeat for 5 s → SAFE state, relay forced off. |
| | `$ALRM,124,CLEAR*7C` | Door and light back to normal. |
| Answer, done | `$ACK,43,OK*4A` | The command with counter 43 was carried out. |
| Answer, refused | `$ACK,44,REJECT,STATE*3D` | Reason after REJECT (table below). |

The counter in `BOOT`, `STAT` and `ALRM` is the **Pico's own** counter. If the Pi sees it jump (say 120 → 123), messages were lost.
The counter in `ACK` is the **Pi's** counter from the command it answers, so the Pi knows which command the answer is for.

## Why a command is refused

| Reason | Example that causes it |
|---|---|
| `CHECKSUM` | The checksum doesn't match — the line was damaged or changed |
| `FORMAT` | Not a message at all, missing fields, counter not a number, checksum not 2 hex digits |
| `TOO_LONG` | Line longer than 64 characters |
| `VALUE` | Known command, value not allowed — e.g. `RELAY=7` |
| `UNKNOWN` | Message type the Pico doesn't know |
| `STATE` | `RELAY=1` while in SAFE state |

When the Pico cannot read the counter (CHECKSUM, FORMAT, TOO_LONG), it answers with counter 0: `$ACK,0,REJECT,CHECKSUM*57`.

## States (the LEDs)

| State | LED | Buzzer | Meaning |
|---|---|---|---|
| START | amber | – | Just started, no heartbeat yet |
| OK | green | – | Heartbeat arriving, network fine |
| NETDOWN | amber | – | Heartbeat arriving, but the Pi says its network is down |
| ALARM | red | beeping | Door open / wire cut, or light in the box |
| SAFE | red | beeping | No heartbeat for 5 s. Relay forced OFF. Leaves SAFE when heartbeats come back, but the relay stays off until a new `RELAY=1` |

If two things are true at once, the most serious one shows: SAFE, then ALARM, then START, then NETDOWN, then OK.

## Checksum in code

Python (Pi and laptop) and MicroPython (Pico) use the same function:

```python
def checksum(body):
    x = 0
    for ch in body:
        x ^= ord(ch)
    return x

line = "$%s*%02X" % (body, checksum(body))
```
