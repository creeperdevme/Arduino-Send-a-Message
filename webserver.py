import os
import time
import logging
import threading

import serial
import serial.tools.list_ports
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)

app = FastAPI(title="Send a Message")

ARDUINO_PORT = os.getenv('ARDUINO_PORT', '').strip()
BAUD_RATE = int(os.getenv('ARDUINO_BAUD', '9600'))
APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
APP_PORT = int(os.getenv('APP_PORT', '3000'))
MAX_LINE_LENGTH = int(os.getenv('MAX_LINE_LENGTH', '16'))
CONNECT_DELAY_SECONDS = int(os.getenv('CONNECT_DELAY_SECONDS', '2'))

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


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Send a Message</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            overflow: hidden;
        }

        /* Subtle animated background dots */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: radial-gradient(circle, #e0e0e0 1px, transparent 1px);
            background-size: 30px 30px;
            opacity: 0.4;
            z-index: 0;
            animation: bgShift 20s linear infinite;
        }

        @keyframes bgShift {
            0% { background-position: 0 0; }
            100% { background-position: 30px 30px; }
        }

        .container {
            position: relative;
            z-index: 1;
            width: 100%;
            max-width: 480px;
            animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            opacity: 0;
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .card {
            background: #ffffff;
            border: 1px solid #e8e8e8;
            border-radius: 24px;
            padding: 48px 40px;
            box-shadow:
                0 1px 3px rgba(0, 0, 0, 0.04),
                0 6px 16px rgba(0, 0, 0, 0.04),
                0 24px 60px rgba(0, 0, 0, 0.06);
            transition: box-shadow 0.4s ease;
        }

        .card:hover {
            box-shadow:
                0 1px 3px rgba(0, 0, 0, 0.04),
                0 8px 24px rgba(0, 0, 0, 0.06),
                0 32px 80px rgba(0, 0, 0, 0.08);
        }

        /* Icon */
        .icon-wrapper {
            width: 56px;
            height: 56px;
            background: #f5f5f5;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 28px;
            transition: transform 0.3s ease, background 0.3s ease;
        }

        .icon-wrapper:hover {
            transform: scale(1.05);
            background: #eeeeee;
        }

        .icon-wrapper svg {
            width: 28px;
            height: 28px;
            color: #1a1a1a;
        }

        h1 {
            font-size: 26px;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 6px;
            letter-spacing: -0.5px;
        }

        .subtitle {
            font-size: 14px;
            color: #888888;
            margin-bottom: 36px;
            font-weight: 400;
            line-height: 1.5;
        }

        /* Input group */
        .input-group {
            margin-bottom: 20px;
            position: relative;
        }

        .input-group label {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 13px;
            font-weight: 600;
            color: #555555;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .char-count {
            font-size: 12px;
            font-weight: 500;
            color: #bbbbbb;
            transition: color 0.3s ease;
        }

        .char-count.warning {
            color: #e74c3c;
        }

        .input-group input {
            width: 100%;
            padding: 14px 18px;
            border: 2px solid #eeeeee;
            border-radius: 14px;
            font-size: 16px;
            font-family: 'Inter', monospace;
            font-weight: 500;
            color: #1a1a1a;
            background: #fafafa;
            transition: all 0.3s ease;
            outline: none;
            letter-spacing: 0.3px;
        }

        .input-group input::placeholder {
            color: #cccccc;
            font-weight: 400;
        }

        .input-group input:focus {
            border-color: #1a1a1a;
            background: #ffffff;
            box-shadow: 0 0 0 4px rgba(26, 26, 26, 0.06);
        }

        .input-group input.invalid {
            border-color: #e74c3c;
            animation: shake 0.4s ease;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            20% { transform: translateX(-6px); }
            40% { transform: translateX(6px); }
            60% { transform: translateX(-4px); }
            80% { transform: translateX(4px); }
        }

        .error-text {
            font-size: 12px;
            color: #e74c3c;
            margin-top: 6px;
            display: none;
            animation: fadeIn 0.3s ease;
        }

        .error-text.show {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Send button */
        .send-btn {
            width: 100%;
            padding: 16px;
            margin-top: 16px;
            border: none;
            border-radius: 14px;
            background: #1a1a1a;
            color: #ffffff;
            font-family: 'Inter', sans-serif;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            letter-spacing: 0.3px;
        }

        .send-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
            transition: left 0.5s ease;
        }

        .send-btn:hover::before {
            left: 100%;
        }

        .send-btn:hover {
            background: #333333;
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(26, 26, 26, 0.2);
        }

        .send-btn:active {
            transform: translateY(0);
            box-shadow: 0 4px 12px rgba(26, 26, 26, 0.15);
        }

        .send-btn:disabled {
            background: #cccccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .send-btn:disabled::before {
            display: none;
        }

        .btn-content {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-content svg {
            width: 18px;
            height: 18px;
            transition: transform 0.3s ease;
        }

        .send-btn:hover .btn-content svg {
            transform: translateX(3px);
        }

        /* Loading spinner */
        .spinner {
            display: none;
            width: 20px;
            height: 20px;
            border: 2.5px solid rgba(255,255,255,0.3);
            border-top-color: #ffffff;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
            margin: 0 auto;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .send-btn.loading .btn-content { display: none; }
        .send-btn.loading .spinner { display: block; }

        /* Toast notification */
        .toast {
            position: fixed;
            top: 30px;
            left: 50%;
            transform: translateX(-50%) translateY(-100px);
            padding: 14px 28px;
            border-radius: 14px;
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            font-weight: 500;
            z-index: 1000;
            transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 8px 32px rgba(0,0,0,0.12);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .toast.show {
            transform: translateX(-50%) translateY(0);
        }

        .toast.success {
            background: #1a1a1a;
            color: #ffffff;
        }

        .toast.error {
            background: #e74c3c;
            color: #ffffff;
        }

        .toast svg {
            width: 18px;
            height: 18px;
            flex-shrink: 0;
        }

        /* Footer */
        .footer {
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #cccccc;
            font-weight: 400;
        }
    </style>
</head>
<body>

    <!-- Toast notification -->
    <div class="toast" id="toast">
        <span id="toast-icon"></span>
        <span id="toast-message"></span>
    </div>

    <div class="container">
        <div class="card">
            <!-- Icon -->
            <div class="icon-wrapper">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"/>
                </svg>
            </div>

            <h1>Send a Message</h1>
            <p class="subtitle">Enter your message below. English characters and symbols only, 16 characters max per line.</p>

            <form id="messageForm" onsubmit="return false;">
                <!-- Line 1 -->
                <div class="input-group">
                    <label for="line1">
                        Line 1
                        <span class="char-count" id="count1">0 / 16</span>
                    </label>
                    <input
                        type="text"
                        id="line1"
                        name="line1"
                        maxlength="16"
                        placeholder="Enter Line 1..."
                        autocomplete="off"
                        spellcheck="false"
                    >
                    <div class="error-text" id="error1">Only English letters and symbols are allowed.</div>
                </div>

                <!-- Line 2 -->
                <div class="input-group">
                    <label for="line2">
                        Line 2
                        <span class="char-count" id="count2">0 / 16</span>
                    </label>
                    <input
                        type="text"
                        id="line2"
                        name="line2"
                        maxlength="16"
                        placeholder="Enter Line 2..."
                        autocomplete="off"
                        spellcheck="false"
                    >
                    <div class="error-text" id="error2">Only English letters and symbols are allowed.</div>
                </div>

                <!-- Send Button -->
                <button type="submit" class="send-btn" id="sendBtn" onclick="sendMessage()">
                    <div class="btn-content">
                        <span>Send Message</span>
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"/>
                        </svg>
                    </div>
                    <div class="spinner"></div>
                </button>
            </form>
        </div>


    </div>

    <script>
        // Only allow ASCII printable characters (English + symbols, no Unicode/CJK)
        const VALID_PATTERN = /^[\\x20-\\x7E]*$/;

        const line1Input = document.getElementById('line1');
        const line2Input = document.getElementById('line2');
        const count1 = document.getElementById('count1');
        const count2 = document.getElementById('count2');
        const error1 = document.getElementById('error1');
        const error2 = document.getElementById('error2');
        const sendBtn = document.getElementById('sendBtn');

        function validateInput(input, errorEl) {
            const value = input.value;
            // Remove any non-ASCII printable characters immediately
            const filtered = value.replace(/[^\\x20-\\x7E]/g, '');
            if (filtered !== value) {
                input.value = filtered;
                errorEl.classList.add('show');
                input.classList.add('invalid');
                setTimeout(() => {
                    errorEl.classList.remove('show');
                    input.classList.remove('invalid');
                }, 2000);
            }
        }

        function updateCount(input, countEl) {
            const len = input.value.length;
            countEl.textContent = len + ' / 16';
            if (len >= 16) {
                countEl.classList.add('warning');
            } else {
                countEl.classList.remove('warning');
            }
        }

        line1Input.addEventListener('input', () => {
            validateInput(line1Input, error1);
            updateCount(line1Input, count1);
        });

        line2Input.addEventListener('input', () => {
            validateInput(line2Input, error2);
            updateCount(line2Input, count2);
        });

        // Prevent paste of invalid content
        function handlePaste(e, input, errorEl) {
            e.preventDefault();
            const paste = (e.clipboardData || window.clipboardData).getData('text');
            const filtered = paste.replace(/[^\\x20-\\x7E]/g, '');
            const remaining = 16 - input.value.length;
            const toInsert = filtered.substring(0, remaining);
            document.execCommand('insertText', false, toInsert);
            validateInput(input, errorEl);
        }

        line1Input.addEventListener('paste', (e) => handlePaste(e, line1Input, error1));
        line2Input.addEventListener('paste', (e) => handlePaste(e, line2Input, error2));

        function showToast(message, type) {
            const toast = document.getElementById('toast');
            const toastMsg = document.getElementById('toast-message');
            const toastIcon = document.getElementById('toast-icon');

            toast.className = 'toast ' + type;

            if (type === 'success') {
                toastIcon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>';
            } else {
                toastIcon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"/></svg>';
            }

            toastMsg.textContent = message;

            requestAnimationFrame(() => {
                toast.classList.add('show');
            });

            setTimeout(() => {
                toast.classList.remove('show');
            }, 3500);
        }

        async function sendMessage() {
            const l1 = line1Input.value.trim();
            const l2 = line2Input.value.trim();

            if (!l1 && !l2) {
                showToast('Please enter at least one line of text.', 'error');
                return;
            }

            // Disable button and show loading
            sendBtn.disabled = true;
            sendBtn.classList.add('loading');

            try {
                const response = await fetch('/api/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ line1: l1, line2: l2 })
                });

                const result = await response.json();

                if (response.ok) {
                    showToast('Message sent successfully!', 'success');
                    line1Input.value = '';
                    line2Input.value = '';
                    updateCount(line1Input, count1);
                    updateCount(line2Input, count2);
                } else {
                    showToast(result.detail || 'Failed to send message.', 'error');
                }
            } catch (err) {
                showToast('Connection error. Is the server running?', 'error');
            } finally {
                sendBtn.disabled = false;
                sendBtn.classList.remove('loading');
            }
        }

        // Allow Enter key to submit
        document.getElementById('messageForm').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });
    </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.post("/api/send")
async def send_message(request: Request):
    """Proxy the message to the Flask server.py running on port 8080."""
    data = await request.json()
    line1 = data.get("line1", "")
    line2 = data.get("line2", "")

    if not line1 and not line2:
        return JSONResponse(
            status_code=400,
            content={"detail": "Please provide at least one line of text."}
        )

    try:
        # Enforce the same line length constraints server-side as well.
        if len(line1) > 16 or len(line2) > 16:
            return JSONResponse(
                status_code=400,
                content={"detail": "Each line must be 16 characters or fewer."}
            )

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                FLASK_API_URL,
                json={"line1": line1, "line2": line2}
            )
            return JSONResponse(
                status_code=resp.status_code,
                content={"message": resp.text}
            )
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={"detail": "Cannot connect to display server. Is server.py running?"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal error: {str(e)}"}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
