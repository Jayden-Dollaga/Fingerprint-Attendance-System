/************************************************************************************
 *  AS608 Fingerprint - All-in-One Sketch
 *  ESP32 WROOM-32 with Screw Terminal Shield
 *
 *  Replaces all 4 Phase 1 sketches with a single file.
 *  No need to re-upload when switching between enrolling and scanning.
 *
 *  Wiring (confirmed working):
 *    Sensor V+ (purple) -> Shield V terminal
 *    Sensor GND (blue)  -> Shield G terminal
 *    Sensor TX (orange) -> Shield S terminal, D14 row  <- ESP32 RX
 *    Sensor RX (white)  -> Shield S terminal, D27 row  <- ESP32 TX
 *
 *  ── COMMANDS (type in Serial Monitor, line ending = Newline) ──
 *
 *    ENROLL        Enroll a new finger using the next free ID
 *    ENROLL:1      Enroll a new finger as ID 1
 *    ENROLL:5      Enroll a new finger as ID 5
 *    DELETE:1      Delete finger ID 1
 *    WIPE          Delete ALL stored fingerprints
 *    LIST          Show how many fingerprints are stored
 *    SCAN          Switch to attendance scan mode
 *    STOP          Stop scanning, go back to command mode
 *
 *  ── TYPICAL WORKFLOW FOR A CLASS OF 30 ──
 *
 *    1. Upload this sketch once, never touch it again
 *    2. Open Serial Monitor at 115200, line ending = Newline
 *    3. Type ENROLL:1  -> scan student 1 finger twice -> saved
 *    4. Type ENROLL:2  -> scan student 2 finger twice -> saved
 *    5. Repeat up to ENROLL:30
 *    6. Type SCAN      -> now reading attendance, Python can connect
 *    7. Type STOP      -> go back to command mode anytime
 *
 *  ── SERIAL OUTPUT FORMAT (what Python reads in SCAN mode) ──
 *
 *    READY           System booted
 *    ID:1            Matched fingerprint ID
 *    CONFIDENCE:223  Match confidence score
 *    UNKNOWN         Finger not recognized
 *    SCAN_MODE       Entered scan mode
 *    CMD_MODE        Entered command mode
 ************************************************************************************/

#include <Adafruit_Fingerprint.h>
#include <HardwareSerial.h>

#define FINGERPRINT_RX   14    // orange wire (sensor TX) connects here
#define FINGERPRINT_TX   27    // white wire  (sensor RX) connects here
#define MIN_CONFIDENCE   50    // minimum confidence to accept a match
#define SCAN_COOLDOWN    2000  // ms to wait after a scan before scanning again

HardwareSerial mySerial(2);
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&mySerial);

// ── Mode ──────────────────────────────────────────────────────────────────────
bool scanMode = false;  // false = command mode, true = scan mode
String pendingCommand = "";


// ==============================================================================
//  SETUP
// ==============================================================================

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n========================================");
  Serial.println("  AS608 All-in-One Fingerprint System");
  Serial.println("========================================");

  mySerial.begin(57600, SERIAL_8N1, FINGERPRINT_RX, FINGERPRINT_TX);
  finger.begin(57600);

  if (finger.verifyPassword()) {
    Serial.println("Sensor found!");
  } else {
    Serial.println("ERROR: Sensor not found. Check wiring.");
    while (1) { delay(1); }
  }

  finger.getTemplateCount();
  Serial.print("Stored fingerprints: ");
  Serial.println(finger.templateCount);

  printHelp();
  Serial.println("READY");
}


// ==============================================================================
//  LOOP
// ==============================================================================

void loop() {
  // Process any pending command that was received during enrollment.
  if (pendingCommand.length() > 0) {
    String cmd = pendingCommand;
    pendingCommand = "";
    handleCommand(cmd);
    return;
  }

  // Check for Serial commands from PC
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    handleCommand(input);
  }

  // If in scan mode, keep scanning for fingers
  if (scanMode) {
    scanFinger();
  }
}


// ==============================================================================
//  COMMAND HANDLER
// ==============================================================================

void handleCommand(String input) {
  input.toUpperCase();

  // ── SCAN ──────────────────────────────────────────────────────
  if (input == "SCAN") {
    scanMode = true;
    Serial.println("\n>> Switched to SCAN MODE");
    Serial.println("   Place finger on sensor to log attendance.");
    Serial.println("   Type STOP to return to command mode.");
    Serial.println("SCAN_MODE");
    return;
  }

  // ── STOP ──────────────────────────────────────────────────────
  if (input == "STOP") {
    scanMode = false;
    Serial.println("\n>> Switched to COMMAND MODE");
    printHelp();
    Serial.println("CMD_MODE");
    return;
  }

  // ── LIST ──────────────────────────────────────────────────────
  if (input == "LIST") {
    scanMode = false;
    finger.getTemplateCount();
    Serial.print("\n>> Stored fingerprints: ");
    Serial.println(finger.templateCount);
    Serial.println("CMD_MODE");
    return;
  }

  // ── WIPE ──────────────────────────────────────────────────────
  if (input == "WIPE") {
    scanMode = false;
    Serial.println("\n>> Wiping ALL fingerprints...");
    if (finger.emptyDatabase() == FINGERPRINT_OK) {
      Serial.println("   SUCCESS - All fingerprints deleted.");
    } else {
      Serial.println("   FAILED - Could not wipe database.");
    }
    Serial.println("CMD_MODE");
    return;
  }

  // ── ENROLL / ENROLL:ID ──────────────────────────────────────
  if (input == "ENROLL") {
    int id = findNextAvailableId();
    if (id <= 0) {
      Serial.println("ERROR: No free fingerprint slots available. Delete one first.");
      return;
    }
    scanMode = false; // pause scanning during enrollment
    enrollFinger(id);
    return;
  }

  if (input.startsWith("ENROLL:")) {
    int id = input.substring(7).toInt();
    if (id < 1 || id > 127) {
      Serial.println("ERROR: ID must be between 1 and 127. Example: ENROLL:5");
      return;
    }
    scanMode = false; // pause scanning during enrollment
    enrollFinger(id);
    return;
  }

  // ── DELETE:ID ─────────────────────────────────────────────────
  if (input.startsWith("DELETE:")) {
    int id = input.substring(7).toInt();
    if (id < 1 || id > 127) {
      Serial.println("ERROR: ID must be between 1 and 127. Example: DELETE:5");
      return;
    }
    Serial.print("\n>> Deleting ID #");
    Serial.print(id);
    Serial.println("...");
    if (finger.deleteModel(id) == FINGERPRINT_OK) {
      Serial.print("   SUCCESS - ID #");
      Serial.print(id);
      Serial.println(" deleted.");
    } else {
      Serial.print("   FAILED - Could not delete ID #");
      Serial.print(id);
      Serial.println(" (may not exist)");
    }
    return;
  }

  // ── UNKNOWN COMMAND ───────────────────────────────────────────
  Serial.println("Unknown command. Type HELP to see commands.");
  printHelp();
}


// ==============================================================================
//  ENROLL HELPERS
// ==============================================================================

bool fingerprintExists(uint8_t id) {
  uint8_t p = finger.loadModel(id);
  return p == FINGERPRINT_OK;
}

int findNextAvailableId() {
  for (int id = 1; id <= 127; ++id) {
    if (!fingerprintExists(id)) {
      return id;
    }
  }
  return -1;
}

bool checkEnrollmentCancel() {
  if (!Serial.available()) {
    return false;
  }

  String input = Serial.readStringUntil('\n');
  input.trim();
  input.toUpperCase();

  if (input == "STOP") {
    Serial.println("\n>> Enrollment cancelled.");
    Serial.println("ENROLLMENT cancelled.");
    Serial.println("CMD_MODE");
    return true;
  }

  if (input.startsWith("DELETE:") || input.startsWith("ENROLL") || input == "WIPE" || input == "LIST" || input == "SCAN") {
    pendingCommand = input;
    Serial.println("\n>> Enrollment cancelled due to a new command.");
    Serial.println("ENROLLMENT cancelled.");
    Serial.println("CMD_MODE");
    return true;
  }

  if (input.length() > 0) {
    Serial.println("Enrollment is in progress. Type STOP to cancel.");
  }
  return false;
}

// ==============================================================================
//  ENROLL
// ==============================================================================

void enrollFinger(int id) {
  Serial.println();
  Serial.println("----------------------------------------");
  Serial.print("  ENROLLING FINGER AS ID #");
  Serial.println(id);
  Serial.println("----------------------------------------");

  int p = -1;

  // ── SCAN 1 ────────────────────────────────────────────────────
  Serial.println("Step 1: Place finger on sensor...");
  while (p != FINGERPRINT_OK) {
    if (checkEnrollmentCancel()) {
      return;
    }
    p = finger.getImage();
    if (p == FINGERPRINT_NOFINGER) { Serial.print("."); continue; }
    if (p == FINGERPRINT_OK)       { Serial.println("\n  Image taken!"); break; }
    Serial.println("  Imaging error, try again.");
  }

  p = finger.image2Tz(1);
  if (p != FINGERPRINT_OK) {
    Serial.println("  ERROR: Could not convert image. Try again.");
    Serial.println("  Tip: Press finger flat and firm on the sensor.");
    return;
  }
  Serial.println("  Image converted.");

  // ── LIFT FINGER ───────────────────────────────────────────────
  Serial.println("Step 2: Remove finger...");
  unsigned long start_wait = millis();
  while (millis() - start_wait < 2000) {
    if (checkEnrollmentCancel()) {
      return;
    }
    delay(50);
  }
  p = 0;
  while (p != FINGERPRINT_NOFINGER) {
    if (checkEnrollmentCancel()) {
      return;
    }
    p = finger.getImage();
  }
  Serial.println("  Finger removed.");

  // ── SCAN 2 ────────────────────────────────────────────────────
  Serial.println("Step 3: Place the SAME finger again...");
  p = -1;
  while (p != FINGERPRINT_OK) {
    if (checkEnrollmentCancel()) {
      return;
    }
    p = finger.getImage();
    if (p == FINGERPRINT_NOFINGER) { Serial.print("."); continue; }
    if (p == FINGERPRINT_OK)       { Serial.println("\n  Image taken!"); break; }
    Serial.println("  Imaging error, try again.");
  }

  p = finger.image2Tz(2);
  if (p != FINGERPRINT_OK) {
    Serial.println("  ERROR: Could not convert image. Try again.");
    return;
  }
  Serial.println("  Image converted.");

  // ── CREATE MODEL ──────────────────────────────────────────────
  p = finger.createModel();
  if (p == FINGERPRINT_ENROLLMISMATCH) {
    Serial.println("  ERROR: Fingerprints did not match.");
    Serial.println("  Tip: Use the SAME finger, same position, both times.");
    Serial.print("  Type ENROLL:");
    Serial.print(id);
    Serial.println(" to try again.");
    return;
  }
  if (p != FINGERPRINT_OK) {
    Serial.println("  ERROR: Could not create model.");
    return;
  }

  // ── STORE ─────────────────────────────────────────────────────
  p = finger.storeModel(id);
  if (p == FINGERPRINT_OK) {
    Serial.println("----------------------------------------");
    Serial.print("  SUCCESS! Finger saved as ID #");
    Serial.println(id);
    Serial.println("----------------------------------------");
    finger.getTemplateCount();
    Serial.print("  Total stored: ");
    Serial.println(finger.templateCount);
    Serial.println();
  } else {
    Serial.println("  ERROR: Could not store fingerprint.");
  }
}


// ==============================================================================
//  SCAN (Attendance Mode)
// ==============================================================================

void scanFinger() {
  uint8_t p = finger.getImage();
  if (p == FINGERPRINT_NOFINGER) return;
  if (p != FINGERPRINT_OK)       return;

  p = finger.image2Tz();
  if (p != FINGERPRINT_OK) return;

  p = finger.fingerSearch();
  if (p == FINGERPRINT_OK) {
    if (finger.confidence >= MIN_CONFIDENCE) {
      Serial.print("ID:");
      Serial.println(finger.fingerID);
      Serial.print("CONFIDENCE:");
      Serial.println(finger.confidence);
    } else {
      Serial.println("UNKNOWN");
      Serial.print("LOW_CONFIDENCE:");
      Serial.println(finger.confidence);
    }
    delay(SCAN_COOLDOWN);
  } else if (p == FINGERPRINT_NOTFOUND) {
    Serial.println("UNKNOWN");
    delay(1000);
  }
}


// ==============================================================================
//  HELP
// ==============================================================================

void printHelp() {
  Serial.println();
  Serial.println("  Commands (line ending must be set to Newline):");
  Serial.println("    ENROLL     Enroll finger using next free ID");
  Serial.println("    ENROLL:1   Enroll finger as ID 1  (1-127)");
  Serial.println("    DELETE:1   Delete finger ID 1");
  Serial.println("    WIPE       Delete ALL fingerprints");
  Serial.println("    LIST       Show stored fingerprint count");
  Serial.println("    SCAN       Start attendance scan mode");
  Serial.println("    STOP       Stop scanning, return to commands");
  Serial.println();
}
