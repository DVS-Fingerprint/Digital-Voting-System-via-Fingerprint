/*
 * ESP32 Scanner Authentication Example
 * This code demonstrates how ESP32 communicates with Django server for voter authentication
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
const char* scannerAuthUrl = "/voting/api/scanner-authenticate/";

// Fingerprint sensor configuration
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&Serial2);

// Global variables
bool authenticationRequested = false;
unsigned long lastCheckTime = 0;
const unsigned long checkInterval = 1000; // Check every 1 second

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
  // Check for fingerprint on sensor
  uint8_t p = finger.getImage();
  if (p == FINGERPRINT_OK) {
    Serial.println("Fingerprint detected!");
    authenticateFingerprint();
  } else if (p == FINGERPRINT_NOFINGER) {
    // No finger detected, continue
  } else {
    Serial.println("Error getting image");
  }
  
  delay(100);
}

void authenticateFingerprint() {
  Serial.println("Processing fingerprint...");
  
  // Convert image to template
  uint8_t p = finger.image2Tz(1);
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
  
  // Convert template to hex string
  String templateHex = "";
  for (int i = 0; i < sizeof(finger.template); i++) {
    if (finger.template[i] < 16) {
      templateHex += "0";
    }
    templateHex += String(finger.template[i], HEX);
  }
  
  Serial.println("Template converted to hex");
  
  // Send to Django server for authentication
  sendToServer(templateHex);
}

void sendToServer(String templateHex) {
  HTTPClient http;
  String url = String(serverUrl) + scannerAuthUrl;
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  DynamicJsonDocument doc(2048);
  doc["template_hex"] = templateHex;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  Serial.println("Sending authentication request...");
  Serial.println("URL: " + url);
  Serial.println("Payload: " + jsonString);
  
  int httpCode = http.POST(jsonString);
  
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.println("Authentication response: " + payload);
    
    // Parse response
    DynamicJsonDocument responseDoc(1024);
    deserializeJson(responseDoc, payload);
    
    if (responseDoc["status"] == "ok") {
      Serial.println("✅ Authentication successful!");
      Serial.println("Voter: " + responseDoc["name"].as<String>());
      Serial.println("Confidence: " + responseDoc["confidence"].as<String>());
    } else if (responseDoc["status"] == "already_voted") {
      Serial.println("⚠️ Voter has already voted");
      Serial.println("Voter: " + responseDoc["name"].as<String>());
    } else if (responseDoc["status"] == "not_found") {
      Serial.println("❌ Fingerprint not recognized");
    } else {
      Serial.println("❌ Authentication failed");
    }
  } else {
    Serial.println("Error sending authentication request. HTTP Code: " + String(httpCode));
    String payload = http.getString();
    Serial.println("Error response: " + payload);
  }
  
  http.end();
}

/*
 * Serial Monitor Output Example:
 * 
 * Connecting to WiFi...
 * WiFi connected
 * IP address: 192.168.1.101
 * Fingerprint sensor found!
 * Fingerprint detected!
 * Processing fingerprint...
 * Template created
 * Template converted to hex
 * Sending authentication request...
 * URL: http://192.168.1.100:8000/voting/api/scanner-authenticate/
 * Payload: {"template_hex":"a1b2c3d4e5f6..."}
 * Authentication response: {"status":"ok","name":"John Doe","confidence":0.95}
 * ✅ Authentication successful!
 * Voter: John Doe
 * Confidence: 0.95
 */ 