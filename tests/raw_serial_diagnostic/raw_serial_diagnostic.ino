#include <Adafruit_Fingerprint.h>

HardwareSerial mySerial(2);
Adafruit_Fingerprint finger(&mySerial);

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Starting sensor check...");

  mySerial.begin(57600, SERIAL_8N1, 14, 27); // RX=14, TX=27
  delay(100);

  if (finger.verifyPassword()) {
    Serial.println("SUCCESS: Sensor found!");
  } else {
    Serial.println("FAILED: Sensor not found, check wiring.");
  }
}

void loop() {
}