#include <Adafruit_Fingerprint.h>

#define RX_PIN 16
#define TX_PIN 17
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&Serial2);

void setup() {
  Serial.begin(9600);
  Serial2.begin(57600, SERIAL_8N1, RX_PIN, TX_PIN);
  finger.begin(57600);

  if (finger.verifyPassword()) {
    Serial.println("Found fingerprint sensor!");
  } else {
    Serial.println("Did not find fingerprint sensor :(");
    while (1) { delay(1); }
  }
}

void loop() {
  Serial.println("Type in the ID # you want to enroll (1-127), then press Enter:");
  while (!Serial.available());
  int id = Serial.parseInt();
  while (Serial.available()) Serial.read(); // clear buffer

  if (id < 1 || id > 127) {
    Serial.println("Invalid ID. Please use 1-127.");
    return;
  }

  Serial.print("Enrolling ID #"); Serial.println(id);
  enrollFingerprint(id);
}

void enrollFingerprint(int id) {
  int p = -1;
  Serial.println("Place finger on sensor...");
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
  }
  p = finger.image2Tz(1);
  if (p != FINGERPRINT_OK) { Serial.println("Failed to convert image"); return; }
  Serial.println("Remove finger");
  delay(2000);
  Serial.println("Place same finger again...");
  p = -1;
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
  }
  p = finger.image2Tz(2);
  if (p != FINGERPRINT_OK) { Serial.println("Failed to convert image"); return; }
  p = finger.createModel();
  if (p != FINGERPRINT_OK) { Serial.println("Failed to create model"); return; }
  p = finger.storeModel(id);
  if (p == FINGERPRINT_OK) {
    Serial.print("Fingerprint enrolled successfully! Use UID: F");
    Serial.println(id);
  } else {
    Serial.println("Failed to store fingerprint");
  }
}