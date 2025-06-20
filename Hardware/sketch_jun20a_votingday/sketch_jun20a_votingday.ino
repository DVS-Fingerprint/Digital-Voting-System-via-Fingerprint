#include <WiFi.h>
#include <HTTPClient.h>
#include <Adafruit_Fingerprint.h>

// WiFi and server config
const char* ssid = "sameer837_fpkhr";                // <-- CHANGE THIS
const char* password = "9762335022";        // <-- CHANGE THIS
const char* authUrl = "http://YOUR_DJANGO_SERVER_IP:8000/api/authenticate_fingerprint/"; // <-- CHANGE THIS

// AS608 wiring
#define RX_PIN 16
#define TX_PIN 17
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&Serial2);

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Start Serial2 for AS608
  Serial2.begin(57600, SERIAL_8N1, RX_PIN, TX_PIN);
  finger.begin(57600);

  if (finger.verifyPassword()) {
    Serial.println("Found fingerprint sensor!");
  } else {
    Serial.println("Did not find fingerprint sensor :(");
    while (1) { delay(1); }
  }

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  Serial.println("Place finger on sensor...");
  int uid = getFingerprintID();
  if (uid > 0) {
    String voterUID = "F" + String(uid);
    authenticateVoter(voterUID);
  }
  delay(3000); // Wait before next scan
}

int getFingerprintID() {
  uint8_t p = finger.getImage();
  if (p != FINGERPRINT_OK) return -1;
  p = finger.image2Tz();
  if (p != FINGERPRINT_OK) return -1;
  p = finger.fingerSearch();
  if (p == FINGERPRINT_OK) {
    Serial.print("Found ID #"); Serial.println(finger.fingerID);
    return finger.fingerID;
  } else {
    Serial.println("No match found");
    return -1;
  }
}

void authenticateVoter(String uid) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(authUrl);
    http.addHeader("Content-Type", "application/json");
    String payload = "{\"uid\": \"" + uid + "\"}";
    int httpResponseCode = http.POST(payload);
    String response = http.getString();
    Serial.print("Auth response: ");
    Serial.println(response);
    http.end();

    if (response.indexOf("\"status\":\"ok\"") != -1) {
      Serial.println("Authentication successful. Show voting UI.");
      // TODO: Add code to show voting UI or send vote
    } else if (response.indexOf("\"status\":\"already_voted\"") != -1) {
      Serial.println("You have already voted!");
    } else {
      Serial.println("Authentication failed.");
    }
  } else {
    Serial.println("WiFi not connected!");
  }
}