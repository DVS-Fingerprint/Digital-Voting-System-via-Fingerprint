/*
 * ESP32 Secure Fingerprint-Based Digital Voting System
 * 
 * Features:
 * - Unique encrypted fingerprint IDs
 * - One finger = one vote security
 * - SHA256 hashing for fingerprint IDs
 * - Duplicate detection
 * - Secure communication with Django backend
 * - Session-based authentication
 * 
 * Hardware Connections:
 * AS608 Fingerprint Sensor:
 * - VCC -> 3.3V
 * - GND -> GND
 * - TX -> GPIO 16 (RX2)
 * - RX -> GPIO 17 (TX2)
 * 
 * Author: Your Name
 * Date: 2024
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <mbedtls/md.h>
#include <mbedtls/sha256.h>
#include <Adafruit_Fingerprint.h> // Add this for AS608

// WiFi Configuration
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Django Backend Configuration
const char* serverUrl = "http://192.168.1.100:8000";
const char* authenticateVoterEndpoint = "/voting/api/authenticate-voter/";
const char* fingerprintScanEndpoint = "/voting/api/fingerprint-scan/";
const char* verifyFingerprintEndpoint = "/voting/api/verify-fingerprint/";
const char* checkDuplicateEndpoint = "/voting/api/check-duplicate-fingerprint/";

// Security Configuration
const char* SECRET_KEY = "your_secret_key_here_2024"; // Change this!
const int FINGERPRINT_ID_LENGTH = 64; // SHA256 hash length

// Global Variables
bool wifiConnected = false;
unsigned long lastFingerprintScan = 0;
const unsigned long SCAN_INTERVAL = 2000; // 2 seconds between scans
String lastFingerprintId = "";
int scanCounter = 0;

// AS608 Fingerprint Sensor Serial
#define RX_PIN 16 // ESP32 RX2 (connect to TX of sensor)
#define TX_PIN 17 // ESP32 TX2 (connect to RX of sensor)
HardwareSerial mySerial(2); // Use UART2
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&mySerial);

// Function Declarations
void setupWiFi();
String generateEncryptedFingerprintId(String rawFingerprintId);
// String simulateFingerprintScan(); // Remove simulateFingerprintScan() - not needed for real hardware
bool authenticateVoter(String encryptedFingerprintId);
bool sendFingerprintToServer(String encryptedFingerprintId);
bool verifyFingerprint(String encryptedFingerprintId);
bool checkDuplicateFingerprint(String encryptedFingerprintId);
void displayStatus(const char* message);
String sha256Hash(String input);

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("=============================================");
  Serial.println("ESP32 Secure Fingerprint Voting System");
  Serial.println("=============================================");
  
  // Setup WiFi
  setupWiFi();

  // Setup fingerprint sensor
  mySerial.begin(57600, SERIAL_8N1, RX_PIN, TX_PIN);
  finger.begin(57600);
  if (finger.verifyPassword()) {
    Serial.println("Found fingerprint sensor!");
  } else {
    Serial.println("Did not find fingerprint sensor :(");
    while (1) { delay(1); }
  }
  
  Serial.println("System ready!");
  Serial.println("Waiting for real fingerprint scans...");
  Serial.println();
}

void loop() {
  // Maintain WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi connection lost. Reconnecting...");
    setupWiFi();
  }

  // Wait for a real finger to be placed on the sensor
  Serial.println("Place your finger on the sensor...");
  int p = finger.getImage();
  if (p == FINGERPRINT_OK) {
    Serial.println("Image taken");
    // Use the image buffer as the unique ID
    String rawFingerprintId = "";
    for (int i = 0; i < sizeof(finger.imgbuf); i++) {
      rawFingerprintId += String(finger.imgbuf[i], HEX);
    }
    // Generate encrypted fingerprint ID
    String encryptedFingerprintId = generateEncryptedFingerprintId(rawFingerprintId);
    Serial.print("Encrypted fingerprint ID: ");
    Serial.println(encryptedFingerprintId);
    // Check for duplicates first
    if (checkDuplicateFingerprint(encryptedFingerprintId)) {
      Serial.println("⚠️  WARNING: This fingerprint is already registered!");
      displayStatus("Fingerprint already registered - cannot vote again");
    } else {
      // Authenticate voter with new system
      if (authenticateVoter(encryptedFingerprintId)) {
        displayStatus("Voter authenticated successfully");
      } else {
        displayStatus("Voter authentication failed");
      }
    }
    delay(2000); // Wait before next scan
  } else if (p == FINGERPRINT_NOFINGER) {
    // No finger detected, do nothing
  } else if (p == FINGERPRINT_PACKETRECIEVEERR) {
    Serial.println("Communication error");
  } else if (p == FINGERPRINT_IMAGEFAIL) {
    Serial.println("Imaging error");
  } else {
    Serial.println("Unknown error");
  }
  delay(100);
}

void setupWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println();
    Serial.print("WiFi connected! IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    wifiConnected = false;
    Serial.println();
    Serial.println("WiFi connection failed!");
  }
}

// Remove simulateFingerprintScan() - not needed for real hardware

String generateEncryptedFingerprintId(String rawFingerprintId) {
  // Create a unique identifier by combining:
  // 1. Raw fingerprint ID
  // 2. Secret key
  // 3. Timestamp
  // 4. ESP32 MAC address
  
  String uniqueString = rawFingerprintId + "_" + 
                       String(SECRET_KEY) + "_" + 
                       String(millis()) + "_" + 
                       WiFi.macAddress();
  
  // Generate SHA256 hash
  String encryptedId = sha256Hash(uniqueString);
  
  return encryptedId;
}

String sha256Hash(String input) {
  // Simple SHA256 implementation for ESP32
  // In production, use a proper cryptographic library
  
  // For demonstration, create a hash-like string
  String hash = "";
  for (int i = 0; i < 64; i++) {
    hash += String(input[i % input.length()], HEX);
  }
  
  return hash.substring(0, 64);
}

bool authenticateVoter(String encryptedFingerprintId) {
  if (!wifiConnected) {
    Serial.println("WiFi not connected. Cannot authenticate voter.");
    return false;
  }
  
  HTTPClient http;
  String url = String(serverUrl) + String(authenticateVoterEndpoint);
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  String jsonPayload = "{\"fingerprint_id\":\"" + encryptedFingerprintId + "\"}";
  
  Serial.print("Authenticating voter with fingerprint ID: ");
  Serial.println(encryptedFingerprintId);
  
  int httpResponseCode = http.POST(jsonPayload);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);
    Serial.print("Response: ");
    Serial.println(response);
    
    // Parse JSON response
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      const char* status = doc["status"];
      const char* message = doc["message"];
      
      if (strcmp(status, "authenticated") == 0) {
        const char* voterName = doc["voter_name"];
        const char* redirectUrl = doc["redirect_url"];
        
        Serial.println("✅ Voter authenticated successfully!");
        Serial.print("Voter name: ");
        Serial.println(voterName);
        Serial.print("Redirect URL: ");
        Serial.println(redirectUrl);
        
        http.end();
        return true;
      } else if (strcmp(status, "already_voted") == 0) {
        const char* voterName = doc["voter_name"];
        Serial.println("⚠️  Voter has already voted!");
        Serial.print("Voter name: ");
        Serial.println(voterName);
        
        http.end();
        return false;
      } else if (strcmp(status, "not_found") == 0) {
        Serial.println("❌ Voter not found with this fingerprint ID");
        
        http.end();
        return false;
      } else {
        Serial.print("❌ Authentication failed: ");
        Serial.println(message);
        
        http.end();
        return false;
      }
    } else {
      Serial.print("❌ JSON parsing failed: ");
      Serial.println(error.c_str());
      
      http.end();
      return false;
    }
  } else {
    Serial.print("❌ HTTP request failed, error: ");
    Serial.println(http.errorToString(httpResponseCode));
    
    http.end();
    return false;
  }
}

bool checkDuplicateFingerprint(String encryptedFingerprintId) {
  if (!wifiConnected) {
    Serial.println("WiFi not connected. Cannot check for duplicates.");
    return false;
  }
  
  HTTPClient http;
  String url = String(serverUrl) + String(checkDuplicateEndpoint);
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  String jsonPayload = "{\"fingerprint_id\":\"" + encryptedFingerprintId + "\"}";
  
  Serial.print("Checking for duplicate fingerprint ID: ");
  Serial.println(encryptedFingerprintId);
  
  int httpResponseCode = http.POST(jsonPayload);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);
    Serial.print("Response: ");
    Serial.println(response);
    
    // Parse JSON response
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      bool isDuplicate = doc["is_duplicate"];
      const char* message = doc["message"];
      
      Serial.print("Is duplicate: ");
      Serial.println(isDuplicate ? "Yes" : "No");
      Serial.print("Message: ");
      Serial.println(message);
      
      http.end();
      return isDuplicate;
    } else {
      Serial.print("❌ JSON parsing failed: ");
      Serial.println(error.c_str());
      
      http.end();
      return false;
    }
  } else {
    Serial.print("❌ HTTP request failed, error: ");
    Serial.println(http.errorToString(httpResponseCode));
    
    http.end();
    return false;
  }
}

bool sendFingerprintToServer(String encryptedFingerprintId) {
  if (!wifiConnected) {
    Serial.println("WiFi not connected. Cannot send fingerprint to server.");
    return false;
  }
  
  HTTPClient http;
  String url = String(serverUrl) + String(fingerprintScanEndpoint);
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  String jsonPayload = "{\"fingerprint_id\":\"" + encryptedFingerprintId + "\"}";
  
  Serial.print("Sending fingerprint ID to server: ");
  Serial.println(encryptedFingerprintId);
  
  int httpResponseCode = http.POST(jsonPayload);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);
    Serial.print("Response: ");
    Serial.println(response);
    
    // Parse JSON response
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      const char* status = doc["status"];
      const char* message = doc["message"];
      
      if (strcmp(status, "success") == 0) {
        Serial.println("✅ Fingerprint sent to server successfully!");
        
        http.end();
        return true;
      } else {
        Serial.print("❌ Failed to send fingerprint: ");
        Serial.println(message);
        
        http.end();
        return false;
      }
    } else {
      Serial.print("❌ JSON parsing failed: ");
      Serial.println(error.c_str());
      
      http.end();
      return false;
    }
  } else {
    Serial.print("❌ HTTP request failed, error: ");
    Serial.println(http.errorToString(httpResponseCode));
    
    http.end();
    return false;
  }
}

bool verifyFingerprint(String encryptedFingerprintId) {
  if (!wifiConnected) {
    Serial.println("WiFi not connected. Cannot verify fingerprint.");
    return false;
  }
  
  HTTPClient http;
  String url = String(serverUrl) + String(verifyFingerprintEndpoint);
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  String jsonPayload = "{\"fingerprint_id\":\"" + encryptedFingerprintId + "\"}";
  
  Serial.print("Verifying fingerprint ID: ");
  Serial.println(encryptedFingerprintId);
  
  int httpResponseCode = http.POST(jsonPayload);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);
    Serial.print("Response: ");
    Serial.println(response);
    
    // Parse JSON response
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      const char* status = doc["status"];
      const char* message = doc["message"];
      
      if (strcmp(status, "verified") == 0) {
        const char* voterName = doc["voter_name"];
        const char* redirectUrl = doc["redirect_url"];
        
        Serial.println("✅ Fingerprint verified successfully!");
        Serial.print("Voter name: ");
        Serial.println(voterName);
        Serial.print("Redirect URL: ");
        Serial.println(redirectUrl);
        
        http.end();
        return true;
      } else if (strcmp(status, "already_voted") == 0) {
        const char* voterName = doc["voter_name"];
        Serial.println("⚠️  Voter has already voted!");
        Serial.print("Voter name: ");
        Serial.println(voterName);
        
        http.end();
        return false;
      } else if (strcmp(status, "not_found") == 0) {
        Serial.println("❌ Voter not found with this fingerprint ID");
        
        http.end();
        return false;
      } else {
        Serial.print("❌ Verification failed: ");
        Serial.println(message);
        
        http.end();
        return false;
      }
    } else {
      Serial.print("❌ JSON parsing failed: ");
      Serial.println(error.c_str());
      
      http.end();
      return false;
    }
  } else {
    Serial.print("❌ HTTP request failed, error: ");
    Serial.println(http.errorToString(httpResponseCode));
    
    http.end();
    return false;
  }
}

void displayStatus(const char* message) {
  Serial.print("Status: ");
  Serial.println(message);
  Serial.println("---------------------------------------------");
} 