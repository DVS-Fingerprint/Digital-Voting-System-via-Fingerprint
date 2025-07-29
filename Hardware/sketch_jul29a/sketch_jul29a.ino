#include <WiFi.h>
#include <HTTPClient.h>

// Wi-Fi credentials
const char* ssid = "Sameer837__wlink";
const char* password = "9819158546";

// Django API endpoints
const char* TRIGGER_URL = "http://192.168.2.100:8000/api/scan-trigger/";
const char* UPLOAD_URL  = "http://192.168.2.100:8000/api/upload-template/";
const char* MATCH_URL   = "http://192.168.2.100:8000/api/match-template/";

// Fingerprint sensor UART config
#define RX_PIN 16
#define TX_PIN 17
#define SENSOR Serial2

// AS608 constants
#define AS608_ADDRESS 0xFFFFFFFF
#define CMD_UPLOAD_TEMPLATE 0x08
#define CMD_IMAGE2TZ 0x02
#define CMD_GET_IMAGE 0x01
#define CMD_CHAR_BUFFER_1 0x01
#define TEMPLATE_SIZE 512

uint8_t templateBuffer[TEMPLATE_SIZE];
const char base64_chars[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

// === Base64 encoding utility ===
String base64Encode(const uint8_t* data, size_t len) {
  String output;
  uint8_t a3[3], a4[4];
  int i = 0;

  while (len--) {
    a3[i++] = *(data++);
    if (i == 3) {
      a4[0] = (a3[0] & 0xfc) >> 2;
      a4[1] = ((a3[0] & 0x03) << 4) + ((a3[1] & 0xf0) >> 4);
      a4[2] = ((a3[1] & 0x0f) << 2) + ((a3[2] & 0xc0) >> 6);
      a4[3] = a3[2] & 0x3f;
      for (i = 0; i < 4; i++) output += base64_chars[a4[i]];
      i = 0;
    }
  }

  if (i) {
    for (int j = i; j < 3; j++) a3[j] = '\0';
    a4[0] = (a3[0] & 0xfc) >> 2;
    a4[1] = ((a3[0] & 0x03) << 4) + ((a3[1] & 0xf0) >> 4);
    a4[2] = ((a3[1] & 0x0f) << 2) + ((a3[2] & 0xc0) >> 6);
    a4[3] = a3[2] & 0x3f;
    for (int j = 0; j < i + 1; j++) output += base64_chars[a4[j]];
    while (i++ < 3) output += '=';
  }

  return output;
}

// Write packet to sensor
void writePacket(uint8_t* packet, uint16_t length) {
  SENSOR.write(0xEF); SENSOR.write(0x01);
  SENSOR.write((AS608_ADDRESS >> 24) & 0xFF);
  SENSOR.write((AS608_ADDRESS >> 16) & 0xFF);
  SENSOR.write((AS608_ADDRESS >> 8) & 0xFF);
  SENSOR.write((AS608_ADDRESS >> 0) & 0xFF);
  SENSOR.write(0x01); // Command packet
  SENSOR.write((length >> 8) & 0xFF);
  SENSOR.write((length >> 0) & 0xFF);

  uint16_t checksum = 0x01 + (length >> 8) + (length & 0xFF);
  for (int i = 0; i < length - 2; i++) {
    SENSOR.write(packet[i]);
    checksum += packet[i];
  }

  SENSOR.write((checksum >> 8) & 0xFF);
  SENSOR.write((checksum >> 0) & 0xFF);
}

// Wait for ACK with expected code
bool getACK(uint8_t expectedCode) {
  long timeout = millis() + 2000;
  while (SENSOR.available() < 12 && millis() < timeout);
  if (SENSOR.available() < 12) return false;

  uint8_t response[12];
  SENSOR.readBytes(response, 12);
  return (response[6] == 0x07 && response[9] == expectedCode);
}

// Capture and convert fingerprint image
bool captureAndConvert() {
  uint8_t cmd1[] = {CMD_GET_IMAGE};
  writePacket(cmd1, 3);
  if (!getACK(0x00)) return false;
  delay(500);

  uint8_t cmd2[] = {CMD_IMAGE2TZ, CMD_CHAR_BUFFER_1};
  writePacket(cmd2, 4);
  if (!getACK(0x00)) return false;

  return true;
}

// Download template from sensor buffer #1
bool downloadTemplate(uint8_t* buf) {
  uint8_t cmd[] = {CMD_UPLOAD_TEMPLATE, CMD_CHAR_BUFFER_1};
  writePacket(cmd, 4);
  if (!getACK(0x00)) return false;

  int received = 0;
  while (received < TEMPLATE_SIZE) {
    long timeout = millis() + 2000;
    while (SENSOR.available() < 9 && millis() < timeout);
    if (SENSOR.available() < 9) return false;

    uint8_t header[9];
    SENSOR.readBytes(header, 9);

    if (header[6] != 0x02 && header[6] != 0x08) return false;

    uint16_t dataLen = (header[7] << 8) | header[8];
    dataLen -= 2;

    while (SENSOR.available() < dataLen + 2 && millis() < timeout);
    if (SENSOR.available() < dataLen + 2) return false;

    SENSOR.readBytes(buf + received, dataLen);
    SENSOR.read(); SENSOR.read();  // skip checksum
    received += dataLen;
  }

  return true;
}

void flushSensorInput() {
  while (SENSOR.available()) SENSOR.read();
}

void waitForFingerToBeRemoved() {
  Serial.println("🕐 Please remove your finger...");
  bool removed = false;
  for (int i = 0; i < 50; i++) {
    uint8_t cmd[] = {CMD_GET_IMAGE};
    writePacket(cmd, 3);
    delay(250);
    if (getACK(0x02)) {
      Serial.println("✅ Finger removed.");
      removed = true;
      break;
    }
  }
  if (!removed) {
    Serial.println("⚠ Sensor still thinks finger is present... continuing anyway.");
  }
  flushSensorInput();
  delay(500);
}

// Poll backend for scan trigger (returns voter_id or -1 if none)
int pollForScanTrigger(String& action_out) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected");
    return -1;
  }

  HTTPClient http;
  http.begin(TRIGGER_URL);
  int httpCode = http.GET();
  if (httpCode != 200) {
    Serial.printf("Failed to get scan trigger, code: %d\n", httpCode);
    http.end();
    return -1;
  }

  String payload = http.getString();
  http.end();

  // Parse JSON manually (simple parsing)
  int userIdx = payload.indexOf("voter_id");
  int actionIdx = payload.indexOf("action");

  if (userIdx < 0 || actionIdx < 0) return -1;

  int colonUser = payload.indexOf(":", userIdx);
  int commaUser = payload.indexOf(",", userIdx);
  if (colonUser < 0 || commaUser < 0) return -1;

  String userIdStr = payload.substring(colonUser + 1, commaUser);
  userIdStr.trim();

  int colonAction = payload.indexOf(":", actionIdx);
  int commaAction = payload.indexOf("}", actionIdx);
  if (colonAction < 0 || commaAction < 0) return -1;

  action_out = payload.substring(colonAction + 2, commaAction - 1); // assumes "action":"register"
  action_out.trim();

  return userIdStr.toInt();
}

// Send template to backend
bool sendTemplateToBackend(const String& base64Data, int voter_id, const String& action) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected.");
    return false;
  }

  HTTPClient http;
  String url = (action == "register") ? UPLOAD_URL : MATCH_URL;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  String payload;
  if (action == "register") {
    payload = "{\"user_id\": " + String(voter_id) + ", \"template_hex\": \"" + base64Data + "\"}";
  } else {
    payload = "{\"template\": \"" + base64Data + "\"}";
  }

  int res = http.POST(payload);
  if (res > 0) {
    String response = http.getString();
    Serial.printf("✅ Backend responded %d: %s\n", res, response.c_str());
    http.end();
    return true;
  } else {
    Serial.printf("❌ HTTP POST failed: %s\n", http.errorToString(res).c_str());
    http.end();
    return false;
  }
}

void setup() {
  Serial.begin(115200);
  SENSOR.begin(57600, SERIAL_8N1, RX_PIN, TX_PIN);

  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi connected.");

  flushSensorInput();
  waitForFingerToBeRemoved();
}

void loop() {
  Serial.println("⏳ Polling backend for scan trigger...");
  String action = "";
  int voter_id = pollForScanTrigger(action);

  if (voter_id == -1) {
    delay(3000);
    return;  // no trigger
  }

  Serial.printf("⚡ Trigger received for voter_id=%d action=%s\n", voter_id, action.c_str());
  Serial.println("👉 Place finger on sensor...");

  long start_time = millis();
  bool captured = false;
  while (millis() - start_time < 15000) {
    if (captureAndConvert()) {
      captured = true;
      break;
    }
    delay(500);
  }
  if (!captured) {
    Serial.println("❌ Failed to capture fingerprint. Aborting.");
    waitForFingerToBeRemoved();
    delay(1000);
    return;
  }

  if (!downloadTemplate(templateBuffer)) {
    Serial.println("❌ Failed to download fingerprint template.");
    waitForFingerToBeRemoved();
    delay(1000);
    return;
  }

  Serial.println("✅ Template captured. Encoding...");
  String base64Template = base64Encode(templateBuffer, TEMPLATE_SIZE);

  if (sendTemplateToBackend(base64Template, voter_id, action)) {
    Serial.println("✅ Template sent successfully.");
  } else {
    Serial.println("❌ Failed to send template.");
  }

  waitForFingerToBeRemoved();
  delay(1000);
}