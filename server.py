from flask import Flask, request
import serial
import time
import logging

# --- Configure Logging ---
# This will display logs with the time, log level (INFO/WARNING/ERROR), and the message.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)

app = Flask(__name__)

# --- Arduino Serial Configuration ---
# Remember to change 'COM3' to your actual Port (e.g., /dev/ttyACM0 for Linux/Mac)
ARDUINO_PORT = 'COM3'  
BAUD_RATE = 9600

# Attempt to connect to Arduino
try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) # Give Arduino 2 seconds to reset and initialize
    logging.info(f"Successfully connected to Arduino on {ARDUINO_PORT}")
except Exception as e:
    logging.error(f"Failed to connect to Arduino on {ARDUINO_PORT}: {e}")
    arduino = None

@app.route('/v1/display', methods=['GET', 'POST'])
def display_text():
    line1 = ""
    line2 = ""
    
    # Handle GET or POST requests
    if request.method == 'GET':
        line1 = request.args.get('line1', '')
        line2 = request.args.get('line2', '')
    elif request.method == 'POST':
        data = request.get_json()
        if data:
            line1 = data.get('line1', '')
            line2 = data.get('line2', '')

    # Check if both lines are empty (WARNING)
    if not line1 and not line2:
        warning_msg = "No text provided for line1 or line2."
        logging.warning(f"Bad Request: {warning_msg}")
        return f"Warning: {warning_msg} Example: http://127.0.0.1:8080/v1/display?line1=Hello&line2=World", 400

    if arduino:
        try:
            # Combine the lines with '|' as a separator and '\n' as the end character
            payload = f"{line1}|{line2}\n"
            arduino.write(payload.encode('utf-8'))
            
            # Log successful transmission (INFO)
            logging.info(f"Sent to Arduino -> Line 1: '{line1}' | Line 2: '{line2}'")
            return f"Success!\nLine 1: '{line1}'\nLine 2: '{line2}'", 200
            
        except Exception as e:
            # Log transmission failure (ERROR)
            error_msg = f"Failed to send data to Arduino: {e}"
            logging.error(error_msg)
            return f"Error: {error_msg}", 500
    else:
        # Log missing connection (ERROR)
        logging.error("Attempted to send data, but Arduino is not connected.")
        return "Error: Arduino is not connected. Please check your USB connection.", 500

if __name__ == '__main__':
    logging.info("Starting Web Server on port 8080...")
    app.run(host='0.0.0.0', port=8080)
