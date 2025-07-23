import serial
import requests
import time

COM_PORT = 'COM6'
BAUD_RATE = 115200
API_ENDPOINT = 'http://localhost:8000/api/upload-template/'
USER_ID = 1

def read_template_from_serial():
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    print(f"Connected to {COM_PORT}. Waiting for template data...")

    template_lines = []
    start_time = time.time()

    while True:
        if time.time() - start_time > 30:  # 30 seconds timeout
            print("Timeout: No template data received in 30 seconds.")
            break

        if ser.in_waiting > 0:
            line = ser.readline().decode(errors='ignore').strip()
            if not line:
                continue
            # Reset timer on receiving data to allow more time if data continues
            start_time = time.time()

            if "Template sent successfully" in line:
                break
            if all(c in "0123456789ABCDEFabcdef" for c in line.replace(" ", "")):
                template_lines.append(line)

    ser.close()
    hex_template = ''.join(template_lines).replace(" ", "")
    print(f"Received template ({len(hex_template)} hex chars)")
    return hex_template

def send_to_django(template_hex):
    payload = {
        'user_id': USER_ID,
        'template_hex': template_hex
    }
    response = requests.post(API_ENDPOINT, json=payload)
    if response.status_code == 200:
        print("✅ Uploaded successfully.")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    template_hex = read_template_from_serial()
    if template_hex:
        send_to_django(template_hex)
    else:
        print("No template data to send.")
