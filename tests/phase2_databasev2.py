###############################################################################
#  Phase 2 - Serial Reader + SQLite Database Logger (Improved)
#  AS608 Fingerprint Attendance System
#
#  Improvements applied:
#    1. Normalized database - attendance only stores fingerprint_id, no repeats
#    2. datetime instead of time.strftime()
#    3. Duplicate scan protection - same ID ignored within 10 seconds
#    4. Serial reading separated from database logic
#    5. Configuration block at top for easy editing
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
import os
import time
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────
COM_PORT          = "COM5"
BAUD_RATE         = 115200
DB_FILE           = "attendance_system.db"
COOLDOWN_SECONDS  = 10
# ──────────────────────────────────────────────────────────────────────────────


def init_database(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            fingerprint_id  INTEGER PRIMARY KEY,
            student_no      TEXT    NOT NULL,
            student_name    TEXT    NOT NULL,
            grade           TEXT    NOT NULL,
            section         TEXT    NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint_id  INTEGER NOT NULL,
            date            TEXT    NOT NULL,
            time            TEXT    NOT NULL,
            confidence      INTEGER NOT NULL,
            status          TEXT    NOT NULL,
            FOREIGN KEY (fingerprint_id) REFERENCES students(fingerprint_id)
        )
    """)
    conn.commit()
    print(f"Database ready: {os.path.abspath(DB_FILE)}")


def add_sample_students(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        sample_students = [
            (1, "2026001", "Jayden",   "12", "STEM-A"),
            (2, "2026002", "Student2", "12", "STEM-A"),
            (3, "2026003", "Student3", "12", "STEM-A"),
            (4, "2026004", "Student4", "12", "STEM-A"),
        ]
        cursor.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?)", sample_students)
        conn.commit()
        print("Sample students loaded.\n")


def get_student(conn, fingerprint_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT student_no, student_name, grade, section FROM students WHERE fingerprint_id = ?",
        (fingerprint_id,)
    )
    row = cursor.fetchone()
    if row:
        return {"student_no": row[0], "student_name": row[1], "grade": row[2], "section": row[3]}
    return None


def log_attendance(conn, fingerprint_id, confidence, status, now):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO attendance (fingerprint_id, date, time, confidence, status)
        VALUES (?, ?, ?, ?, ?)
    """, (
        fingerprint_id,
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S"),
        confidence,
        status,
    ))
    conn.commit()


def read_line(esp32):
    if esp32.in_waiting > 0:
        raw = esp32.readline()
        try:
            return raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            return None
    return None


def parse_scan(esp32):
    line = read_line(esp32)
    if line is None:
        return None, None

    if line.startswith("ID:"):
        current_id = int(line.split(":")[1])
        for _ in range(20):
            conf_line = read_line(esp32)
            if conf_line and conf_line.startswith("CONFIDENCE:"):
                return current_id, int(conf_line.split(":")[1])

    elif line == "UNKNOWN":
        print(">>> Finger not recognized\n")
    elif line == "READY":
        print(">>> ESP32 is online and ready\n")
    elif line and not any(line.startswith(x) for x in
         ["rst:", "load:", "entry", "config", "mode:", "ho ", "clk_"]):
        print(f"[ESP32] {line}")

    return None, None


def main():
    print("=" * 55)
    print("  AS608 Fingerprint Attendance System - Phase 2")
    print("=" * 55)

    conn = sqlite3.connect(DB_FILE)
    init_database(conn)
    add_sample_students(conn)

    print(f"Connecting to ESP32 on {COM_PORT}...")
    try:
        esp32 = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print("Connected! Waiting for fingerprint scans...\n")
    except serial.SerialException as e:
        print(f"ERROR: Could not connect to {COM_PORT}\nDetails: {e}")
        print("\nFixes:\n  - Close Arduino Serial Monitor\n  - Check ESP32 is plugged in")
        conn.close()
        return

    last_scan = {}

    try:
        while True:
            fingerprint_id, confidence = parse_scan(esp32)
            if fingerprint_id is None:
                continue

            now = datetime.now()

            # Duplicate protection
            if fingerprint_id in last_scan:
                seconds_since = (now - last_scan[fingerprint_id]).total_seconds()
                if seconds_since < COOLDOWN_SECONDS:
                    print(f">>> Duplicate ignored (ID:{fingerprint_id}, {seconds_since:.1f}s ago)\n")
                    continue

            last_scan[fingerprint_id] = now

            # Look up student
            student = get_student(conn, fingerprint_id)
            if student is None:
                student = {
                    "student_no": "N/A",
                    "student_name": f"Unknown ID:{fingerprint_id}",
                    "grade": "N/A",
                    "section": "N/A",
                }
                print(f"WARNING: ID {fingerprint_id} not in students table. Logging as unknown.\n")

            status = "GOOD MATCH" if confidence >= 100 else "WEAK MATCH"
            log_attendance(conn, fingerprint_id, confidence, status, now)

            print("─" * 45)
            print(f"  SCAN LOGGED")
            print("─" * 45)
            print(f"  Name         : {student['student_name']}")
            print(f"  Student No.  : {student['student_no']}")
            print(f"  Grade        : {student['grade']}")
            print(f"  Section      : {student['section']}")
            print(f"  Date         : {now.strftime('%Y-%m-%d')}")
            print(f"  Time         : {now.strftime('%H:%M:%S')}")
            print(f"  Confidence   : {confidence}")
            print(f"  Status       : {status}")
            print("─" * 45)
            print()

    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C)")
    finally:
        esp32.close()
        conn.close()
        print("Connections closed.")


if __name__ == "__main__":
    main()