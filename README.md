# Arduino-Send-a-Message

Type a message in your browser, and it shows up on a 16×2 LCD wired to an Arduino — with a short double beep to announce it.

The Arduino listens on the serial port. A small Python web server runs on your PC, serves a web form, and forwards whatever you type down the USB cable.

```text
Browser  ──HTTP──▶  Python web server  ──USB serial──▶  Arduino  ──▶  LCD + Buzzer
                    (FastAPI / Flask)    9600 baud       "line1|line2\n"
```

---

## Features

- **Web UI** — clean single-page form with live character counter, input validation, and toast notifications
- **Auto port detection** — finds the Arduino automatically, or point it at a port explicitly
- **Two lines, 16 characters each** — matches the LCD exactly
- **Non-ASCII filtering** — CJK and other unsupported characters are stripped before they reach the display
- **Audible alert** — the buzzer beeps twice on every new message
- **Hot reconnect** — if the USB cable is unplugged and replugged, the next request reconnects on its own

---

## Hardware

| Part | Notes |
| --- | --- |
| Arduino Uno / Nano | Any board with a hardware serial port and enough 5 V pins |
| 16×2 LCD with I2C backpack | Default I2C address `0x27` |
| Passive buzzer | Must be on a PWM pin — the sketch uses pin **9** to control volume |

### Wiring

| LCD (I2C) | Arduino Uno/Nano |
| --- | --- |
| GND | GND |
| VCC | 5V |
| SDA | A4 |
| SCL | A5 |

| Buzzer | Arduino |
| --- | --- |
| `+` | D9 (PWM) |
| `−` | GND |

> On a Mega or a board with different I2C pins, adjust the SDA/SCL wiring accordingly. If your LCD stays blank, run an I2C scanner sketch — some backpacks ship at `0x3F` instead of `0x27`, and you'll need to change the address in [main.ino](main.ino).

---

## Software setup

### 1. Arduino

1. Install the **LiquidCrystal_I2C** library (by Frank de Brabander) via *Tools → Manage Libraries*.
2. Open [main.ino](main.ino) and upload it to your board.
3. The LCD should greet you with `Server Ready!`.

### 2. Python

Requires Python 3.8+.

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
python webserver.py
```

Then open <http://127.0.0.1:3000> and send a message.

---

## Configuration

The server reads its settings from environment variables. [.env.example](.env.example) lists them all — copy it and export the values in your shell (the app reads the process environment directly, so you'll need your own `.env` loader or shell profile to use the file as-is).

| Variable | Default | Description |
| --- | --- | --- |
| `ARDUINO_PORT` | *(auto-detect)* | Serial port, e.g. `COM3` (Windows) or `/dev/ttyACM0` (Linux/macOS). Leave blank to let the server scan. |
| `ARDUINO_BAUD` | `9600` | Must match `Serial.begin()` in the sketch |
| `APP_HOST` | `0.0.0.0` | Bind address for the web server |
| `APP_PORT` | `3000` | Web server port |
| `MAX_LINE_LENGTH` | `16` | Characters per LCD line |
| `CONNECT_DELAY_SECONDS` | `2` | Wait after opening the serial port before sending — Arduinos reset on connect |

Example (PowerShell):

```powershell
$env:ARDUINO_PORT = "COM3"
python webserver.py
```

Example (bash):

```bash
ARDUINO_PORT=/dev/ttyACM0 python webserver.py
```

> **Close the Arduino IDE's Serial Monitor before starting the server.** Only one program can hold the serial port, and this is the most common cause of a connection failure.

---

## Usage

### Web interface

Open the server root (`/`) for a two-field form. Each line is capped at 16 characters; anything outside printable ASCII is rejected as you type. On success the form clears and the LCD updates.

### API

Send a message directly:

```bash
curl -X POST http://127.0.0.1:3000/api/send \
  -H "Content-Type: application/json" \
  -d '{"line1": "Hello", "line2": "World"}'
```

```json
{ "message": "Message sent successfully." }
```

Check whether the Arduino is reachable:

```bash
curl http://127.0.0.1:3000/health
# {"status":"ok"}                                   HTTP 200
# {"status":"arduino_not_connected"}                HTTP 503
```

| Method | Path | Body / Query | Returns |
| --- | --- | --- | --- |
| `GET` | `/` | — | The web form |
| `POST` | `/api/send` | JSON `{ "line1": str, "line2": str }` | `200` on success, `400` if both lines are empty, `503` if the Arduino is not connected, `500` on internal error |
| `GET` | `/health` | — | `200` when connected, `503` otherwise |

If only one line is given, the other is blank. Both fields are truncated to `MAX_LINE_LENGTH` and stripped of non-printable-ASCII characters server-side, so the display can't be corrupted by unexpected input.

---

## `webserver.py` vs `server.py`

Both talk to the same sketch over the same serial protocol. They differ in framework and surface area:

| | [webserver.py](webserver.py) | [server.py](server.py) |
| --- | --- | --- |
| Framework | FastAPI + Uvicorn | Flask |
| Web UI | Yes, served at `/` | No |
| Endpoint | `POST /api/send` (JSON) | `GET`/`POST /v1/display` (query params or JSON) |
| Default port | `3000` | `8080` |
| Configurable | Port, host, line length, delay | Port, baud |

**Use `webserver.py`** unless you specifically want the lighter Flask dependency — it's the maintained path and includes the browser interface. `server.py` is the earlier, minimal version, handy if you're wiring this into something that just needs an HTTP endpoint.

---

## Serial protocol

The Arduino expects one newline-terminated message per line of text sent:

```text
line1|line2\n
```

- `|` separates the two display rows. Without it, the whole payload goes on line 1.
- `\n` terminates the message and triggers the display refresh and beep.
- 9600 baud, 8N1.

You can drive the hardware without either Python server, straight from a serial terminal — type `Hello|World` and hit enter.

---

## Project structure

```text
Arduino-Send-a-Message/
├── main.ino          # Arduino sketch — LCD + buzzer, reads serial
├── webserver.py      # FastAPI server with web UI (recommended)
├── server.py         # Minimal Flask server
├── requirements.txt  # Python dependencies
├── .env.example      # Configuration template
└── README.md
```

---

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `Arduino not connected` / `503` | Serial Monitor still open in the Arduino IDE, wrong `ARDUINO_PORT`, or a charge-only USB cable |
| `Multiple serial port candidates found` | Several USB serial devices attached — set `ARDUINO_PORT` explicitly to silence the guess |
| LCD stays blank | I2C address mismatch (`0x27` vs `0x3F`), or the contrast pot on the backpack needs adjusting |
| Garbled or missing characters | `ARDUINO_BAUD` doesn't match `Serial.begin(9600)` in the sketch |
| Message appears with letters missing | Input contained non-ASCII characters — they're filtered by design, since the LCD font can't render them |
| Buzzer silent | It's on a non-PWM pin, or the volume value (`10` in `beepTwice()`) is too low for your buzzer — try `20` |

---

## License

No license file is included in this repository.
