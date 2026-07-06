/*
  ESP32 WROOM-32 + AS608 Fingerprint Sensor
  --------------------------------------------------
  Wiring used in this sketch:
    Sensor TX (Orange) -> ESP32 D14  (ESP32 RX2)
    Sensor RX (White)  -> ESP32 D27  (ESP32 TX2)
    Sensor GND         -> ESP32 GND
    Sensor VCC         -> ESP32 3.3V or 5V (check your module's rating)

  Library required:
    Adafruit Fingerprint Sensor Library
    (Arduino IDE -> Library Manager -> search "Adafruit Fingerprint")

  Open Serial Monitor at 115200 baud after uploading.
  Type commands into the Serial Monitor:
    e -> Enroll a new fingerprint
    f -> Find/verify a fingerprint
    d -> Delete a fingerprint by ID
    c -> Show number of stored fingerprints
*/

#include <Adafruit_Fingerprint.h>
#include <HardwareSerial.h>

// Use ESP32 hardware serial port 2 for the sensor
HardwareSerial fingerSerial(2);           // UART2
Adafruit_Fingerprint finger(&fingerSerial);

#define FINGER_RX_PIN 14   // ESP32 pin connected to sensor TX (Orange)
#define FINGER_TX_PIN 27   // ESP32 pin connected to sensor RX (White)

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }
  delay(100);
  Serial.println("\nESP32 + AS608 Fingerprint Sensor");

  // Sensor typically runs at 57600 baud
  fingerSerial.begin(57600, SERIAL_8N1, FINGER_RX_PIN, FINGER_TX_PIN);
  delay(100);

  if (finger.verifyPassword()) {
    Serial.println("Fingerprint sensor found!");
  } else {
    Serial.println("Fingerprint sensor NOT found :(");
    Serial.println("Check wiring, power, and TX/RX pins (they may need swapping).");
    while (1) { delay(1000); }
  }

  finger.getTemplateCount();
  Serial.print("Sensor contains ");
  Serial.print(finger.templateCount);
  Serial.println(" templates.");

  printMenu();
}

void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();
    switch (cmd) {
      case 'e':
      case 'E':
        enrollFingerprint();
        break;
      case 'f':
      case 'F':
        findFingerprint();
        break;
      case 'd':
      case 'D':
        deleteFingerprint();
        break;
      case 'c':
      case 'C':
        finger.getTemplateCount();
        Serial.print("Templates stored: ");
        Serial.println(finger.templateCount);
        break;
      default:
        break;
    }
    printMenu();
  }
}

void printMenu() {
  Serial.println("\n---- Menu ----");
  Serial.println("e = Enroll new fingerprint");
  Serial.println("f = Find/verify fingerprint");
  Serial.println("d = Delete fingerprint by ID");
  Serial.println("c = Count stored templates");
  Serial.println("--------------");
}

// Reads an ID number typed into the Serial Monitor
int readIDFromSerial() {
  Serial.println("Enter ID number (1-127) and press Enter:");
  while (!Serial.available()) { delay(50); }
  int id = Serial.parseInt();
  // clear any trailing newline
  while (Serial.available()) Serial.read();
  return id;
}

// ---------------- ENROLL ----------------
void enrollFingerprint() {
  int id = readIDFromSerial();
  if (id <= 0 || id > 127) {
    Serial.println("Invalid ID. Must be 1-127.");
    return;
  }

  Serial.print("Enrolling ID #");
  Serial.println(id);

  int p = -1;
  Serial.println("Place finger on sensor...");
  unsigned long enrollStart = millis();
  unsigned long enrollLastPrint = 0;
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    switch (p) {
      case FINGERPRINT_OK:
        Serial.println("Image taken");
        break;
      case FINGERPRINT_NOFINGER:
        if (millis() - enrollLastPrint > 1000) {
          Serial.println("...waiting for finger");
          enrollLastPrint = millis();
        }
        if (millis() - enrollStart > 15000) {
          Serial.println("Timed out waiting for finger. Enrollment cancelled.");
          return;
        }
        break;
      default:
        Serial.print("Error capturing image, code: ");
        Serial.println(p);
        return;
    }
  }

  p = finger.image2Tz(1);
  if (p != FINGERPRINT_OK) {
    Serial.println("Error converting image");
    return;
  }

  Serial.println("Remove finger");
  delay(1500);
  p = 0;
  while (p != FINGERPRINT_NOFINGER) {
    p = finger.getImage();
  }

  Serial.println("Place same finger again...");
  p = -1;
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    switch (p) {
      case FINGERPRINT_OK:
        Serial.println("Image taken");
        break;
      case FINGERPRINT_NOFINGER:
        break;
      default:
        Serial.println("Error capturing image");
        return;
    }
  }

  p = finger.image2Tz(2);
  if (p != FINGERPRINT_OK) {
    Serial.println("Error converting second image");
    return;
  }

  p = finger.createModel();
  if (p != FINGERPRINT_OK) {
    Serial.println("Prints did not match. Try again.");
    return;
  }

  p = finger.storeModel(id);
  if (p == FINGERPRINT_OK) {
    Serial.println("Fingerprint stored successfully!");
  } else {
    Serial.println("Error storing fingerprint");
  }
}

// ---------------- FIND / VERIFY ----------------
void findFingerprint() {
  Serial.println("Place finger to verify...");

  int p = -1;
  unsigned long startTime = millis();
  unsigned long lastPrint = 0;

  while (p != FINGERPRINT_OK) {
    p = finger.getImage();

    if (p == FINGERPRINT_NOFINGER) {
      // print a heartbeat every second so we know the loop is alive
      if (millis() - lastPrint > 1000) {
        Serial.println("...waiting for finger (no finger detected)");
        lastPrint = millis();
      }
      if (millis() - startTime > 10000) {
        Serial.println("Timed out waiting for finger. Try again.");
        return;
      }
      continue;
    }

    if (p == FINGERPRINT_PACKETRECIEVEERR) {
      Serial.println("Communication error while capturing image (packet error).");
      return;
    }

    if (p == FINGERPRINT_IMAGEFAIL) {
      Serial.println("Imaging error - sensor could not capture image.");
      return;
    }

    if (p != FINGERPRINT_OK) {
      Serial.print("Error capturing image, code: ");
      Serial.println(p);
      return;
    }
  }
  Serial.println("Image taken!");

  p = finger.image2Tz();
  if (p != FINGERPRINT_OK) {
    Serial.println("Error converting image");
    return;
  }

  p = finger.fingerSearch();
  if (p == FINGERPRINT_OK) {
    Serial.print("Match found! ID #");
    Serial.print(finger.fingerID);
    Serial.print(" with confidence ");
    Serial.println(finger.confidence);
  } else if (p == FINGERPRINT_NOTFOUND) {
    Serial.println("No match found.");
  } else {
    Serial.println("Error during search.");
  }
}

// ---------------- DELETE ----------------
void deleteFingerprint() {
  int id = readIDFromSerial();
  int p = finger.deleteModel(id);
  if (p == FINGERPRINT_OK) {
    Serial.println("Deleted!");
  } else {
    Serial.println("Failed to delete (ID may not exist).");
  }
}
