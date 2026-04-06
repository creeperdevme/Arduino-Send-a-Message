from flask import Flask, request
import os
import serial
import serial.tools.list_ports
import time
import logging
import threading

# --- Configure Logging ---
# This will display logs with the time, log level (INFO/WARNING/ERROR), and the message.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)

app = Flask(__name__)

# --- Arduino Serial Configuration ---
ARDUINO_PORT = os.getenv('ARDUINO_PORT', '').strip()
BAUD_RATE = int(os.getenv('ARDUINO_BAUD', '9600'))
CONNECT_DELAY_SECONDS = 2

arduino = None
arduino_lock = threading.Lock()


def find_arduino_port():
    if ARDUINO_PORT:
        logging.info(f"Using configured Arduino port: {ARDUINO_PORT}")
        return ARDUINO_PORT

    ports = list(serial.tools.list_ports.comports())
    candidates = []
    for port in ports:
        desc = (port.description or '').lower()
        hwid = (port.hwid or '').lower()
        device = port.device

        if 'arduino' in desc or 'arduino' in hwid:
            candidates.append(device)
        elif 'usb serial' in desc or 'usb serial' in hwid:
            candidates.append(device)
        elif device.lower().startswith('com') or device.lower().startswith('/dev/tty'):
            candidates.append(device)

    if len(candidates) == 1:
        logging.info(f"Auto-detected Arduino port: {candidates[0]}")
        return candidates[0]
    if candidates:
        logging.warning(f"Multiple serial port candidates found: {candidates}. Using {candidates[0]}.")
        return candidates[0]

    logging.error('No serial ports found for Arduino.')
    return None


def connect_arduino():
    global arduino
    port = find_arduino_port()
    if not port:
        return None

    try:
        arduino = serial.Serial(port, BAUD_RATE, timeout=1)
        time.sleep(CONNECT_DELAY_SECONDS)
        logging.info(f"Successfully connected to Arduino on {port}")
        return arduino
    except Exception as e:
        logging.error(f"Failed to connect to Arduino on {port}: {e}")
        arduino = None
        return None


def ensure_connection():
    global arduino
    if arduino and arduino.is_open:
        return True
    return connect_arduino() is not None


def send_payload(payload: str):
    if not ensure_connection():
        raise RuntimeError('Arduino is not connected.')

    with arduino_lock:
        arduino.write(payload.encode('utf-8'))


@app.route('/health', methods=['GET'])
def health():
    if ensure_connection():
        return 'OK', 200
    return 'Arduino not connected', 503


@app.route('/v1/display', methods=['GET', 'POST'])
def display_text():
    line1 = ''
    line2 = ''

    if request.method == 'GET':
        line1 = request.args.get('line1', '')
        line2 = request.args.get('line2', '')
    elif request.method == 'POST':
        data = request.get_json(silent=True)
        if data:
            line1 = data.get('line1', '')
            line2 = data.get('line2', '')

    if not line1 and not line2:
        warning_msg = 'No text provided for line1 or line2.'
        logging.warning(f'Bad Request: {warning_msg}')
        return (
            f'Warning: {warning_msg} Example: http://127.0.0.1:8080/v1/display?line1=Hello&line2=World',
            400,
        )

    line1 = line1[:16]
    line2 = line2[:16]
    payload = f"{line1}|{line2}\n"

    try:
        send_payload(payload)
        logging.info(f"Sent to Arduino -> Line 1: '{line1}' | Line 2: '{line2}'")
        return f"Success!\nLine 1: '{line1}'\nLine 2: '{line2}'", 200
    except Exception as e:
        error_msg = f"Failed to send data to Arduino: {e}"
        logging.error(error_msg)
        return f"Error: {error_msg}", 500


if __name__ == '__main__':
    logging.info('Starting Web Server on port 8080...')
    app.run(host='0.0.0.0', port=8080)
