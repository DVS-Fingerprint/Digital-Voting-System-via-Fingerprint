#include <WiFi.h> 
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Wi-Fi credentials
const char* ssid = "smriti32_fpkhr_2.4";
const char* password = "976818582335_65";

// Django API endpoints
const char* TRIGGER_URL = "http://192.168.1.96:8000/api/scan-trigger/";
const char* UPLOAD_URL  = "http://192.168.1.96:8000/api/upload-template/";
const char* MATCH_URL   = "http://192.168.1.96:8000/api/match-template/";
const char* MARK_USED_URL = "http://192.168.1.96:8000/api/mark-trigger-used/";

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

// Write packet to sensor (your existing packet logic unchanged)
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

// Wait for ACK with expected code (unchanged)
bool getACK(uint8_t expectedCode) {
  long timeout = millis() + 2000;
  while (SENSOR.available() < 12 && millis() < timeout);
  if (SENSOR.available() < 12) return false;

  uint8_t response[12];
  SENSOR.readBytes(response, 12);
  return (response[6] == 0x07 && response[9] == expectedCode);
}

// Capture and convert fingerprint image (unchanged)
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

// Download template from sensor buffer #1 (unchanged)
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

// Poll backend for scan trigger (returns voter_id as string, action string, and trigger id)
bool pollForScanTrigger(String &voter_id_out, String &action_out, int &trigger_id_out) {
  voter_id_out = "";
  action_out = "";
  trigger_id_out = -1;

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected");
    return false;
  }

  HTTPClient http;
  http.begin(TRIGGER_URL);
  int httpCode = http.GET();
  if (httpCode != 200) {
    Serial.printf("Failed to get scan trigger, code: %d\n", httpCode);
    http.end();
    return false;
  }

  String payload = http.getString();
  Serial.println("📦 Received scan trigger JSON:");
  Serial.println(payload);
  http.end();

  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, payload);
  if (error) {
    Serial.print(F("deserializeJson() failed: "));
    Serial.println(error.f_str());
    return false;
  }

  // Extract fields
  if (doc.containsKey("id")) trigger_id_out = doc["id"];
  if (doc.containsKey("voter_id")) voter_id_out = doc["voter_id"].as<String>();
  if (doc.containsKey("action")) action_out = doc["action"].as<String>();

  voter_id_out.trim();
  action_out.trim();

  Serial.printf("⚡ Trigger received: id=%d voter_id=%s action=%s\n", trigger_id_out, voter_id_out.c_str(), action_out.c_str());

  return true;
}
// Send template to backend
// Add triggerId param to this function
bool sendTemplateToBackend(const String& base64Data, const String& voter_id, const String& action, int trigger_id) {
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
    // For registration, send voter_id + template
    payload = "{\"voter_id\": \"" + voter_id + "\", \"template\": \"" + base64Data + "\"}";
  } else {
    // For matching, send trigger_id + template (this is the fix)
    payload = "{\"trigger_id\": " + String(trigger_id) + ", \"template\": \"" + base64Data + "\"}";
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



// Mark the trigger used after successful scan & upload
bool markTriggerUsed(int triggerId) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected.");
    return false;
  }
  HTTPClient http;
  http.begin(MARK_USED_URL);
  http.addHeader("Content-Type", "application/json");

  String payload = "{\"id\": " + String(triggerId) + "}";

  int res = http.POST(payload);
  if (res > 0) {
    String response = http.getString();
    Serial.printf("✅ Marked trigger used: %s\n", response.c_str());
    http.end();
    return true;
  } else {
    Serial.printf("❌ Failed to mark trigger used: %s\n", http.errorToString(res).c_str());
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
  String voter_id = "";
  int trigger_id = -1;

  if (!pollForScanTrigger(voter_id, action, trigger_id)) {
    Serial.println("❌ Failed to parse scan trigger");
    delay(3000);
    return;
  }

  if (trigger_id == -1) {
    delay(3000); // no trigger found, wait and poll again
    return;
  }

  Serial.printf("⚡ Trigger received: id=%d voter_id=%s action=%s\n", trigger_id, voter_id.c_str(), action.c_str());
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

if (sendTemplateToBackend(base64Template, voter_id, action, trigger_id)) {
    Serial.println("✅ Template sent successfully.");

    // Now mark the trigger used on backend
    if (!markTriggerUsed(trigger_id)) {
      Serial.println("❌ Failed to mark trigger used.");
    }
  } else {
    Serial.println("❌ Failed to send template.");
  }

  waitForFingerToBeRemoved();
  delay(1000);
}