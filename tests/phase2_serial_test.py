###############################################################################
#  Phase 2 - Serial Reader Test
#  AS608 Fingerprint Attendance System
#
#  What this does:
#    - Connects to ESP32 on COM5
#    - Reads incoming data
#    - When it sees "ID:X" it prints who scanned
#
#  Run this AFTER uploading Phase1_ESP32_Attendance.ino to the ESP32
#
#  HOW TO RUN:
#    1. Close Arduino Serial Monitor (only one program can use COM port at a time)
#    2. Open terminal in this folder
#    3. Type: python phase2_serial_test.py
#    4. Scan your finger on the sensor
#
###############################################################################

import serial
import time

# ── Settings ──────────────────────────────────────────────────────────────────
COM_PORT  = "COM5"    # Change this if your ESP32 is on a different port
BAUD_RATE = 115200    # Must match Serial.begin() in the Arduino sketch
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  AS608 Attendance System - Serial Test")
    print("=" * 50)
    print(f"Connecting to ESP32 on {COM_PORT}...")

    try:
        # Open serial connection to ESP32
        esp32 = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for ESP32 to boot after serial connects
        print(f"Connected! Waiting for fingerprint scans...\n")

    except serial.SerialException as e:
        print(f"ERROR: Could not connect to {COM_PORT}")
        print(f"Details: {e}")
        print("\nPossible fixes:")
        print("  - Make sure Arduino Serial Monitor is CLOSED")
        print("  - Check ESP32 is plugged in")
        print("  - Verify COM port in Arduino IDE -> Tools -> Port")
        return

    current_id = None  # Holds the ID we just received

    try:
        while True:
            # Read one line from ESP32
            if esp32.in_waiting > 0:
                raw = esp32.readline()

                try:
                    line = raw.decode("utf-8").strip()
                except UnicodeDecodeError:
                    continue  # Skip garbled bytes during boot

                if not line:
                    continue

                # Print everything ESP32 sends (for debugging)
                print(f"[ESP32] {line}")

                # Parse the ID line
                if line.startswith("ID:"):
                    current_id = int(line.split(":")[1])

                # Parse confidence and print the result
                elif line.startswith("CONFIDENCE:") and current_id is not None:
                    confidence = int(line.split(":")[1])
                    print(f"\n>>> Fingerprint detected!")
                    print(f"    ID         : {current_id}")
                    print(f"    Confidence : {confidence}")
                    print(f"    Time       : {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"    Status     : {'GOOD MATCH' if confidence >= 100 else 'WEAK MATCH'}")
                    print()
                    current_id = None  # Reset for next scan

                elif line == "UNKNOWN":
                    print("\n>>> Finger not recognized - not in database\n")

                elif line == "READY":
                    print(">>> ESP32 is online and ready\n")

    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C)")
    finally:
        esp32.close()
        print("Serial connection closed.")

if __name__ == "__main__":
    main()
