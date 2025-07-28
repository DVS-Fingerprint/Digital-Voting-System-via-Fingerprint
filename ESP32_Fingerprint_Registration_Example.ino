/*
 * ESP32 Fingerprint Registration Example
 * This code demonstrates how ESP32 communicates with Django server for voter registration
 * 
 * Requirements:
 * - ESP32 with fingerprint sensor (R307/R308)
 * - WiFi connection
 * - Django server running on your network
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Adafruit_Fingerprint.h>

// WiFi Configuration
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Django Server Configuration
const char* serverUrl = "http://192.168.1.100:8000"; // Replace with your Django server IP
const char* triggerScanUrl = "/voting/api/trigger-scan/";
const char* getScanTriggerUrl = "/voting/api/get-scan-trigger/";
const char* uploadTemplateUrl = "/voting/api/upload-template/";

// Fingerprint sensor configuration
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&Serial2);

// Global variables
String currentVoterId = "";
bool scanTriggered = false;
unsigned long lastPollTime = 0;
const unsigned long pollInterval = 2000; // Poll every 2 seconds

void setup() {
  Serial.begin(115200);
  Serial2.begin(57600);
  
  // Initialize fingerprint sensor
  finger.begin(57600);
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.println("Connecting to WiFi...");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
  
  // Check fingerprint sensor
  if (finger.verifyPassword()) {
    Serial.println("Fingerprint sensor found!");
  } else {
    Serial.println("Fingerprint sensor not found!");
    while (1) { delay(1); }
  }
}

void loop() {
  // Poll for scan triggers
  if (millis() - lastPollTime >= pollInterval) {
    checkForScanTrigger();
    lastPollTime = millis();
  }
  
  // Handle fingerprint sensor
  if (scanTriggered) {
    handleFingerprintScan();
  }
  
  delay(100);
}

void checkForScanTrigger() {
  HTTPClient http;
  String url = String(serverUrl) + getScanTriggerUrl;
  
  http.begin(url);
  int httpCode = http.GET();
  
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, payload);
    
    if (doc["status"] == "trigger_active") {
      String action = doc["action"];
      String voterId = doc["voter_id"];
      
      if (action == "register" && voterId != "") {
        currentVoterId = voterId;
        scanTriggered = true;
        Serial.println("Registration scan triggered for voter: " + currentVoterId);
        Serial.println("Place finger on sensor...");
      }
    }
  }
  
  http.end();
}

void handleFingerprintScan() {
  uint8_t p = finger.getImage();
  if (p != FINGERPRINT_OK) {
    if (p == FINGERPRINT_NOFINGER) {
      return; // No finger detected, continue waiting
    }
    Serial.println("Error getting image");
    return;
  }
  
  Serial.println("Image taken");
  
  // Convert image to template
  p = finger.image2Tz(1);
  if (p != FINGERPRINT_OK) {
    Serial.println("Error converting image to template");
    return;
  }
  
  Serial.println("Template created");
  
  // Get template data
  p = finger.getTemplate();
  if (p != FINGERPRINT_OK) {
    Serial.println("Error getting template");
    return;
  }
  
  // Convert template to base64
  String templateBase64 = base64Encode(finger.template, sizeof(finger.template));
  
  // Upload template to server
  uploadTemplateToServer(templateBase64);
  
  // Reset scan state
  scanTriggered = false;
  currentVoterId = "";
}

void uploadTemplateToServer(String templateBase64) {
  HTTPClient http;
  String url = String(serverUrl) + uploadTemplateUrl;
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  DynamicJsonDocument doc(2048);
  doc["voter_id"] = currentVoterId;
  doc["template"] = templateBase64;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  int httpCode = http.POST(jsonString);
  
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.println("Template uploaded successfully");
    Serial.println("Response: " + payload);
  } else {
    Serial.println("Error uploading template. HTTP Code: " + String(httpCode));
  }
  
  http.end();
}

String base64Encode(uint8_t* data, size_t length) {
  // Simple base64 encoding (you might want to use a proper library)
  const char* base64Chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  String result = "";
  
  for (size_t i = 0; i < length; i += 3) {
    uint32_t chunk = 0;
    chunk |= data[i] << 16;
    if (i + 1 < length) chunk |= data[i + 1] << 8;
    if (i + 2 < length) chunk |= data[i + 2];
    
    result += base64Chars[(chunk >> 18) & 63];
    result += base64Chars[(chunk >> 12) & 63];
    result += (i + 1 < length) ? base64Chars[(chunk >> 6) & 63] : '=';
    result += (i + 2 < length) ? base64Chars[chunk & 63] : '=';
  }
  
  return result;
}

/*th
 * Serial Monitor Output Example:
 * 
 * Connecting to WiFi...
 * WiFi connected
 * IP address: 192.168.1.101
 * Fingerprint sensor found!
 * Registration scan triggered for voter: V000001
 * Place finger on sensor...
 * Image taken
 * Template created
 * Template uploaded successfully
 * Response: {"status":"success","message":"Template captured successfully for registration","voter_id":"V000001","template_hex":"..."}
 */ 