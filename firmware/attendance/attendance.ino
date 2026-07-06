/************************************************************************************
 *  AS608 Fingerprint - Attendance Scanner (Phase 1 Final)
 *  ESP32 WROOM-32 with Screw Terminal Shield
 *
 *  This is the MAIN RUNTIME sketch for the attendance system.
 *  It scans fingers, matches them, and sends the result over USB Serial
 *  in a clean format that Python (Phase 2) can read and log.
 *
 *  Wiring (confirmed working):
 *    Sensor V+ (purple) -> Shield V terminal
 *    Sensor GND (blue)  -> Shield G terminal
 *    Sensor TX (orange) -> Shield S terminal, D14 row  <- ESP32 RX
 *    Sensor RX (white)  -> Shield S terminal, D27 row  <- ESP32 TX
 *
 *  Serial output format (what Python reads):
 *    ID:1          <- matched fingerprint ID number
 *    CONFIDENCE:160  <- match confidence (50-300, higher = better)
 *    UNKNOWN       <- finger not recognized
 *    READY         <- system booted and waiting
 *
 *  NOTE: Run Phase1_ESP32_enroll_fingerprint.ino first to enroll fingers.
 *  NOTE: Keep Serial Monitor CLOSED when Python script is running,
 *        only one program can use the COM port at a time.
 ************************************************************************************/

#include <Adafruit_Fingerprint.h>
#include <HardwareSerial.h>

#define FINGERPRINT_RX 14   // orange wire (sensor TX) connects here
#define FINGERPRINT_TX 27   // white wire  (sensor RX) connects here

// Minimum confidence score to accept a match
// Lower = more lenient, Higher = more strict
// Recommended: 50 (classroom use), 100 (secure use)
#define MIN_CONFIDENCE 50

HardwareSerial mySerial(2);
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&mySerial);

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("AS608 Attendance System - Booting...");

  mySerial.begin(57600, SERIAL_8N1, FINGERPRINT_RX, FINGERPRINT_TX);
  finger.begin(57600);

  if (finger.verifyPassword()) {
    Serial.println("Sensor found!");
  } else {
    Serial.println("ERROR: Sensor not found. Check wiring.");
    while (1) { delay(1); }
  }

  // Show how many fingers are enrolled
  finger.getTemplateCount();
  if (finger.templateCount == 0) {
    Serial.println("WARNING: No fingerprints enrolled yet.");
    Serial.println("Run the enroll sketch first, then re-upload this sketch.");
  } else {
    Serial.print("Enrolled fingerprints: ");
    Serial.println(finger.templateCount);
  }

  // Tell Python the system is ready
  Serial.println("READY");
}

void loop() {
  scanAndSend();
  delay(200);
}

void scanAndSend() {
  // Step 1: Get image from sensor
  uint8_t p = finger.getImage();
  if (p == FINGERPRINT_NOFINGER) return; // no finger, keep waiting silently
  if (p != FINGERPRINT_OK) return;       // imaging error, skip

  // Step 2: Convert image to feature set
  p = finger.image2Tz();
  if (p != FINGERPRINT_OK) return;

  // Step 3: Search stored fingerprints
  p = finger.fingerSearch();

  if (p == FINGERPRINT_OK) {
    // Check confidence threshold
    if (finger.confidence >= MIN_CONFIDENCE) {
      // Send clean format for Python to parse
      Serial.print("ID:");
      Serial.println(finger.fingerID);
      Serial.print("CONFIDENCE:");
      Serial.println(finger.confidence);
    } else {
      // Match found but too weak - treat as unknown
      Serial.println("UNKNOWN");
      Serial.print("LOW_CONFIDENCE:");
      Serial.println(finger.confidence);
    }
    delay(2000); // wait 2 seconds before scanning again (prevents double scan)

  } else if (p == FINGERPRINT_NOTFOUND) {
    Serial.println("UNKNOWN");
    delay(1000);
  }
}
