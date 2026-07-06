/************************************************************************************
 *  AS608 Fingerprint - Delete Utility
 *  ESP32 WROOM-32 with Screw Terminal Shield
 *
 *  Wiring (confirmed working):
 *    Sensor V+ (purple) -> Shield V terminal
 *    Sensor GND (blue)  -> Shield G terminal
 *    Sensor TX (orange) -> Shield S terminal, D14 row
 *    Sensor RX (white)  -> Shield S terminal, D27 row
 *
 *  HOW TO USE:
 *    Open Serial Monitor at 115200 baud, line ending set to "Newline"
 *
 *    To delete ONE fingerprint:
 *      Type:  D1    <- deletes ID #1
 *      Type:  D5    <- deletes ID #5
 *
 *    To wipe ALL fingerprints:
 *      Type:  WIPE
 *
 *    To list how many fingerprints are stored:
 *      Type:  LIST
 ************************************************************************************/

#include <Adafruit_Fingerprint.h>
#include <HardwareSerial.h>

#define FINGERPRINT_RX 14
#define FINGERPRINT_TX 27

HardwareSerial mySerial(2);
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&mySerial);

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\nAS608 Fingerprint Delete Utility");
  Serial.println("Commands:");
  Serial.println("  D<id>  -> Delete specific ID  (example: D1, D5, D10)");
  Serial.println("  WIPE   -> Delete ALL fingerprints");
  Serial.println("  LIST   -> Show how many fingerprints are stored");
  Serial.println("--------------------------------------------------");

  mySerial.begin(57600, SERIAL_8N1, FINGERPRINT_RX, FINGERPRINT_TX);
  finger.begin(57600);

  if (finger.verifyPassword()) {
    Serial.println("Sensor found! Ready.");
  } else {
    Serial.println("Sensor not found :( Check wiring.");
    while (1) { delay(1); }
  }

  // Show count on startup
  finger.getTemplateCount();
  Serial.print("Currently stored fingerprints: ");
  Serial.println(finger.templateCount);
  Serial.println("--------------------------------------------------");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    input.toUpperCase();

    if (input == "WIPE") {
      Serial.println("Wiping ALL fingerprints...");
      if (finger.emptyDatabase() == FINGERPRINT_OK) {
        Serial.println("SUCCESS - All fingerprints deleted.");
      } else {
        Serial.println("FAILED - Could not wipe database.");
      }

    } else if (input == "LIST") {
      finger.getTemplateCount();
      Serial.print("Currently stored fingerprints: ");
      Serial.println(finger.templateCount);

    } else if (input.startsWith("D")) {
      String numStr = input.substring(1);
      uint8_t id = numStr.toInt();
      if (id == 0 || id > 127) {
        Serial.println("Invalid ID. Use D1 to D127.");
        return;
      }
      Serial.print("Deleting ID #");
      Serial.print(id);
      Serial.println("...");
      if (finger.deleteModel(id) == FINGERPRINT_OK) {
        Serial.print("SUCCESS - ID #");
        Serial.print(id);
        Serial.println(" deleted.");
      } else {
        Serial.print("FAILED - Could not delete ID #");
        Serial.println(id);
        Serial.println("(It may not exist in memory)");
      }

    } else {
      Serial.println("Unknown command. Use D<id>, WIPE, or LIST.");
    }
  }
}
