###############################################################################
#  Phase 2 - Serial Reader + SQLite Database Logger
#  AS608 Fingerprint Attendance System
#
#  What this does:
#    - Connects to ESP32 on COM5
#    - Reads fingerprint IDs
#    - Looks up student info from students table
#    - Logs every scan to attendance table
#    - If fingerprint ID has no student assigned, logs as "Unknown ID:X"
#
#  Database: attendance_system.db (created automatically)
#
#  Tables:
#    students   - maps fingerprint ID to student info
#    attendance - logs every scan with timestamp
#
#  HOW TO RUN:
#    1. Close Arduino Serial Monitor
#    2. Open terminal in this folder
#    3. Type: python phase2_database.py
#    4. Scan your finger on the sensor
#
###############################################################################

import serial
import sqlite3
import time
import os

# ── Settings ──────────────────────────────────────────────────────────────────
COM_PORT    = "COM5"                  # Change if ESP32 is on different port
BAUD_RATE   = 115200                  # Must match Serial.begin() in Arduino
DB_FILE     = "attendance_system.db"  # Database file (created automatically)
# ──────────────────────────────────────────────────────────────────────────────


# ==============================================================================
#  DATABASE SETUP
# ==============================================================================

def init_database(conn):
    """Create tables if they don't exist yet."""
    cursor = conn.cursor()

    # Students table - maps fingerprint ID to student info
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            fingerprint_id  INTEGER PRIMARY KEY,
            student_no      TEXT    NOT NULL,
            student_name    TEXT    NOT NULL,
            grade           TEXT    NOT NULL,
            section         TEXT    NOT NULL
        )
    """)

    # Attendance table - logs every scan
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint_id  INTEGER NOT NULL,
            student_no      TEXT    NOT NULL,
            student_name    TEXT    NOT NULL,
            grade           TEXT    NOT NULL,
            section         TEXT    NOT NULL,
            date            TEXT    NOT NULL,
            time            TEXT    NOT NULL,
            confidence      INTEGER NOT NULL,
            status          TEXT    NOT NULL
        )
    """)

    conn.commit()
    print(f"Database ready: {os.path.abspath(DB_FILE)}")


def add_sample_students(conn):
    """
    Add sample students so you can test right away.
    Remove or edit these once you have real student data.
    """
    cursor = conn.cursor()

    # Only insert if students table is empty
    cursor.execute("SELECT COUNT(*) FROM students")
    count = cursor.fetchone()[0]

    if count == 0:
        sample_students = [
            (1, "2026001", "Jayden",  "12", "STEM-A"),
            (2, "2026002", "Student2","12", "STEM-A"),
            (3, "2026003", "Student3","12", "STEM-A"),
            (4, "2026004", "Student4","12", "STEM-A"),
        ]
        cursor.executemany(
            "INSERT INTO students VALUES (?, ?, ?, ?, ?)",
            sample_students
        )
        conn.commit()
        print("Sample students added to database.")
        print("Edit add_sample_students() in this file to add real students.\n")


def get_student(conn, fingerprint_id):
    """Look up student info by fingerprint ID. Returns dict or None."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT student_no, student_name, grade, section FROM students WHERE fingerprint_id = ?",
        (fingerprint_id,)
    )
    row = cursor.fetchone()
    if row:
        return {
            "student_no":   row[0],
            "student_name": row[1],
            "grade":        row[2],
            "section":      row[3],
        }
    return None


def log_attendance(conn, fingerprint_id, student, confidence, status):
    """Save one attendance record to the database."""
    cursor = conn.cursor()
    now  = time.strftime("%Y-%m-%d")
    time_now = time.strftime("%H:%M:%S")

    cursor.execute("""
        INSERT INTO attendance
            (fingerprint_id, student_no, student_name, grade, section, date, time, confidence, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        fingerprint_id,
        student["student_no"],
        student["student_name"],
        student["grade"],
        student["section"],
        now,
        time_now,
        confidence,
        status,
    ))
    conn.commit()
    return now, time_now


# ==============================================================================
#  MAIN
# ==============================================================================

def main():
    print("=" * 55)
    print("  AS608 Fingerprint Attendance System - Phase 2")
    print("=" * 55)

    # ── Connect to database ───────────────────────────────────────
    conn = sqlite3.connect(DB_FILE)
    init_database(conn)
    add_sample_students(conn)

    # ── Connect to ESP32 ─────────────────────────────────────────
    print(f"Connecting to ESP32 on {COM_PORT}...")
    try:
        esp32 = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print("Connected! Waiting for fingerprint scans...\n")
    except serial.SerialException as e:
        print(f"ERROR: Could not connect to {COM_PORT}")
        print(f"Details: {e}")
        print("\nPossible fixes:")
        print("  - Close Arduino Serial Monitor")
        print("  - Check ESP32 is plugged in")
        print("  - Check port in Arduino IDE -> Tools -> Port")
        conn.close()
        return

    current_id = None

    try:
        while True:
            if esp32.in_waiting > 0:
                raw = esp32.readline()

                try:
                    line = raw.decode("utf-8").strip()
                except UnicodeDecodeError:
                    continue

                if not line:
                    continue

                # ── Parse ESP32 output ────────────────────────────
                if line.startswith("ID:"):
                    current_id = int(line.split(":")[1])

                elif line.startswith("CONFIDENCE:") and current_id is not None:
                    confidence = int(line.split(":")[1])
                    status     = "GOOD MATCH" if confidence >= 100 else "WEAK MATCH"

                    # Look up student in database
                    student = get_student(conn, current_id)

                    # Option A: if not found, log as Unknown
                    if student is None:
                        student = {
                            "student_no":   "N/A",
                            "student_name": f"Unknown ID:{current_id}",
                            "grade":        "N/A",
                            "section":      "N/A",
                        }
                        print(f"WARNING: Fingerprint ID {current_id} not in students table.")
                        print(f"         Logging as 'Unknown ID:{current_id}'. Assign a student to this ID in the database.\n")

                    # Log to database
                    date, time_now = log_attendance(conn, current_id, student, confidence, status)

                    # Print result
                    print("─" * 45)
                    print(f"  SCAN LOGGED")
                    print(f"─" * 45)
                    print(f"  Name         : {student['student_name']}")
                    print(f"  Student No.  : {student['student_no']}")
                    print(f"  Grade        : {student['grade']}")
                    print(f"  Section      : {student['section']}")
                    print(f"  Date         : {date}")
                    print(f"  Time         : {time_now}")
                    print(f"  Confidence   : {confidence}")
                    print(f"  Status       : {status}")
                    print(f"─" * 45)
                    print()

                    current_id = None

                elif line == "UNKNOWN":
                    print(">>> Finger not recognized - not enrolled in sensor\n")

                elif line == "READY":
                    print(">>> ESP32 is online and ready\n")

    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C)")
    finally:
        esp32.close()
        conn.close()
        print("Connections closed. Goodbye.")


if __name__ == "__main__":
    main()