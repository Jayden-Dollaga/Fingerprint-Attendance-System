/************************************************************************************
 *  AS608 Fingerprint Enrollment
 *  ESP32 WROOM-32 with Screw Terminal Shield
 *
 *  Wiring (confirmed working):
 *    Sensor V+ (purple) -> Shield V terminal
 *    Sensor GND (blue)  -> Shield G terminal
 *    Sensor TX (orange) -> Shield S terminal, D14 row  <- ESP32 RX
 *    Sensor RX (white)  -> Shield S terminal, D27 row  <- ESP32 TX
 ************************************************************************************/

#include <Adafruit_Fingerprint.h>
#include <HardwareSerial.h>

#define FINGERPRINT_RX 14   // orange wire from sensor TX goes here
#define FINGERPRINT_TX 27   // white wire from sensor RX goes here

HardwareSerial mySerial(2);
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&mySerial);

uint8_t id;

void setup() {
  Serial.begin(115200);   // must match Serial Monitor baud rate
  delay(1000);

  Serial.println("\n\nAS608 Fingerprint Enrollment");

  // Start UART2 with explicit pins - required for ESP32 core 3.x
  mySerial.begin(57600, SERIAL_8N1, FINGERPRINT_RX, FINGERPRINT_TX);
  finger.begin(57600);

  if (finger.verifyPassword()) {
    Serial.println("Sensor found! Ready to enroll.");
  } else {
    Serial.println("Sensor not found :( Check wiring and power.");
    while (1) { delay(1); }
  }

  Serial.println(F("Reading sensor parameters"));
  finger.getParameters();
  Serial.print(F("Status: 0x"));        Serial.println(finger.status_reg, HEX);
  Serial.print(F("Sys ID: 0x"));        Serial.println(finger.system_id, HEX);
  Serial.print(F("Capacity: "));        Serial.println(finger.capacity);
  Serial.print(F("Security level: "));  Serial.println(finger.security_level);
  Serial.print(F("Device address: "));  Serial.println(finger.device_addr, HEX);
  Serial.print(F("Packet len: "));      Serial.println(finger.packet_len);
  Serial.print(F("Baud rate: "));       Serial.println(finger.baud_rate);
}

uint8_t readnumber(void) {
  uint8_t num = 0;
  while (num == 0) {
    while (!Serial.available());
    num = Serial.parseInt();
  }
  return num;
}

void loop() {
  Serial.println("\nReady to enroll a fingerprint!");
  Serial.println("Type the ID # (1 to 127) you want to save this finger as, then press Enter...");
  id = readnumber();
  if (id == 0) {
    Serial.println("ID 0 is not allowed. Try again.");
    return;
  }
  Serial.print("Enrolling ID #");
  Serial.println(id);

  while (!getFingerprintEnroll());
}

uint8_t getFingerprintEnroll() {
  int p = -1;

  // --- SCAN 1 ---
  Serial.print("Waiting for finger to place on sensor (ID #");
  Serial.print(id);
  Serial.println(")...");

  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    switch (p) {
      case FINGERPRINT_OK:
        Serial.println("Image taken!");
        break;
      case FINGERPRINT_NOFINGER:
        Serial.print(".");
        break;
      case FINGERPRINT_PACKETRECIEVEERR:
        Serial.println("Communication error");
        break;
      case FINGERPRINT_IMAGEFAIL:
        Serial.println("Imaging error");
        break;
      default:
        Serial.println("Unknown error");
        break;
    }
  }

  p = finger.image2Tz(1);
  switch (p) {
    case FINGERPRINT_OK:
      Serial.println("Image converted successfully");
      break;
    case FINGERPRINT_IMAGEMESS:
      Serial.println("Image too messy, try again");
      return p;
    case FINGERPRINT_PACKETRECIEVEERR:
      Serial.println("Communication error");
      return p;
    case FINGERPRINT_FEATUREFAIL:
    case FINGERPRINT_INVALIDIMAGE:
      Serial.println("Could not find fingerprint features");
      return p;
    default:
      Serial.println("Unknown error");
      return p;
  }

  // --- LIFT FINGER ---
  Serial.println("Remove your finger now...");
  delay(2000);
  p = 0;
  while (p != FINGERPRINT_NOFINGER) {
    p = finger.getImage();
  }

  // --- SCAN 2 ---
  Serial.println("Place the SAME finger again...");
  p = -1;
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    switch (p) {
      case FINGERPRINT_OK:
        Serial.println("Image taken!");
        break;
      case FINGERPRINT_NOFINGER:
        Serial.print(".");
        break;
      case FINGERPRINT_PACKETRECIEVEERR:
        Serial.println("Communication error");
        break;
      case FINGERPRINT_IMAGEFAIL:
        Serial.println("Imaging error");
        break;
      default:
        Serial.println("Unknown error");
        break;
    }
  }

  p = finger.image2Tz(2);
  switch (p) {
    case FINGERPRINT_OK:
      Serial.println("Image converted successfully");
      break;
    case FINGERPRINT_IMAGEMESS:
      Serial.println("Image too messy, try again");
      return p;
    case FINGERPRINT_PACKETRECIEVEERR:
      Serial.println("Communication error");
      return p;
    case FINGERPRINT_FEATUREFAIL:
    case FINGERPRINT_INVALIDIMAGE:
      Serial.println("Could not find fingerprint features");
      return p;
    default:
      Serial.println("Unknown error");
      return p;
  }

  // --- CREATE MODEL ---
  Serial.print("Creating fingerprint model for ID #");
  Serial.println(id);

  p = finger.createModel();
  if (p == FINGERPRINT_OK) {
    Serial.println("Scans matched!");
  } else if (p == FINGERPRINT_ENROLLMISMATCH) {
    Serial.println("Fingerprints did NOT match - try enrolling again");
    return p;
  } else if (p == FINGERPRINT_PACKETRECIEVEERR) {
    Serial.println("Communication error");
    return p;
  } else {
    Serial.println("Unknown error");
    return p;
  }

  // --- STORE ---
  p = finger.storeModel(id);
  if (p == FINGERPRINT_OK) {
    Serial.print("SUCCESS! Fingerprint saved as ID #");
    Serial.println(id);
  } else if (p == FINGERPRINT_PACKETRECIEVEERR) {
    Serial.println("Communication error");
    return p;
  } else if (p == FINGERPRINT_BADLOCATION) {
    Serial.println("Could not store at that ID location");
    return p;
  } else if (p == FINGERPRINT_FLASHERR) {
    Serial.println("Flash write error");
    return p;
  } else {
    Serial.println("Unknown error");
    return p;
  }

  return true;
}
