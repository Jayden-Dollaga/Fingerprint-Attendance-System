###############################################################################
#  Phase 2 - Serial Reader + SQLite Database Logger
#  AS608 Fingerprint Attendance System
#
#  Full rewrite to match ESP32_Fingerprint_AllInOne.ino
#
#  What this does:
#    - Connects to ESP32 on COM5
#    - Automatically sends SCAN command on connect
#    - Reads fingerprint IDs and logs to SQLite
#    - Handles all commands from the all-in-one sketch
#    - Duplicate scan protection (10 second cooldown)
#    - Logs unknown fingers as "Unknown ID:X"
#
#  HOW TO RUN:
#    1. Close Arduino Serial Monitor
#    2. Open terminal in this folder
#    3. Type: python phase2_database.py
#    4. Scan your finger on the sensor
#
#  COMMANDS (type while running):
#    scan       Tell ESP32 to start scanning
#    stop       Tell ESP32 to stop scanning
#    list       Ask ESP32 how many fingers stored
#    enroll:1   Tell ESP32 to enroll finger as ID 1
#    delete:1   Tell ESP32 to delete finger ID 1
#    wipe       Tell ESP32 to wipe all fingers
#    quit       Exit this program
#
###############################################################################

import serial
import sqlite3
import os
import time
import threading
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────
COM_PORT         = "COM5"
BAUD_RATE        = 115200
DB_FILE          = "attendance_system.db"
COOLDOWN_SECONDS = 10
AUTO_SCAN        = True   # Automatically send SCAN command on connect
# ──────────────────────────────────────────────────────────────────────────────

# ── Boot noise to silently ignore ─────────────────────────────────────────────
IGNORE_PREFIXES = [
    "rst:", "load:", "entry", "configsip", "mode:", "ho ",
    "clk_", "========", "Commands", "ENROLL:", "DELETE:",
    "WIPE", "LIST", "SCAN", "STOP", "Place finger",
    "Enroll finger", "Delete finger", "Delete ALL",
    "Show stored", "Start attendance", "Stop scanning",
    "line ending",
]
# ──────────────────────────────────────────────────────────────────────────────


# ==============================================================================
#  DATABASE
# ==============================================================================

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
    print(f"Database  : {os.path.abspath(DB_FILE)}")


def add_sample_students(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        sample = [
            (1, "2026001", "Jayden",   "12", "STEM-A"),
            (2, "2026002", "Student2", "12", "STEM-A"),
            (3, "2026003", "Student3", "12", "STEM-A"),
            (4, "2026004", "Student4", "12", "STEM-A"),
        ]
        cursor.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?)", sample)
        conn.commit()
        print("Students  : Sample data loaded (edit add_sample_students() for real data)")


def get_student(conn, fingerprint_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT student_no, student_name, grade, section FROM students WHERE fingerprint_id = ?",
        (fingerprint_id,)
    )
    row = cursor.fetchone()
    if row:
        return {"student_no": row[0], "student_name": row[1],
                "grade": row[2], "section": row[3]}
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


# ==============================================================================
#  SERIAL
# ==============================================================================

def should_ignore(line):
    """Returns True for boot noise and help text we don't care about."""
    for prefix in IGNORE_PREFIXES:
        if line.startswith(prefix):
            return True
    return False


def send_command(esp32, cmd):
    """Send a command string to the ESP32."""
    esp32.write((cmd.upper() + "\n").encode("utf-8"))
    print(f"[SENT]    : {cmd.upper()}")


# ==============================================================================
#  INPUT THREAD (lets you type commands while scanning runs)
# ==============================================================================

def input_thread(esp32, stop_event):
    """Runs in background so typing commands doesn't block serial reading."""
    print("\nType commands below (scan / stop / list / enroll:X / delete:X / wipe / quit)\n")
    while not stop_event.is_set():
        try:
            cmd = input()
            if not cmd.strip():
                continue
            if cmd.strip().lower() == "quit":
                print("Exiting...")
                stop_event.set()
                break
            send_command(esp32, cmd.strip())
        except EOFError:
            break


# ==============================================================================
#  MAIN
# ==============================================================================

def main():
    print("=" * 55)
    print("  AS608 Fingerprint Attendance System - Phase 2")
    print("=" * 55)

    # ── Database ──────────────────────────────────────────────────
    conn = sqlite3.connect(DB_FILE)
    init_database(conn)
    add_sample_students(conn)
    print()

    # ── Serial ────────────────────────────────────────────────────
    print(f"Port      : {COM_PORT}")
    try:
        esp32 = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for ESP32 to boot
        print("Status    : Connected!\n")
    except serial.SerialException as e:
        print(f"ERROR: Could not connect to {COM_PORT}")
        print(f"Details   : {e}")
        print("\nFixes:")
        print("  - Close Arduino Serial Monitor")
        print("  - Check ESP32 is plugged in")
        print("  - Check port in Arduino IDE -> Tools -> Port")
        conn.close()
        return

    # Auto-send SCAN command so ESP32 starts scanning immediately
    if AUTO_SCAN:
        time.sleep(0.5)
        send_command(esp32, "SCAN")
        print()

    # ── Start input thread ────────────────────────────────────────
    stop_event = threading.Event()
    t = threading.Thread(target=input_thread, args=(esp32, stop_event), daemon=True)
    t.start()

    # ── State ─────────────────────────────────────────────────────
    current_id   = None
    last_scan    = {}    # {fingerprint_id: datetime of last scan}
    in_scan_mode = False

    try:
        while not stop_event.is_set():
            if esp32.in_waiting == 0:
                time.sleep(0.05)
                continue

            raw = esp32.readline()
            try:
                line = raw.decode("utf-8").strip()
            except UnicodeDecodeError:
                continue

            if not line:
                continue

            # ── Ignore boot noise and help text ───────────────────
            if should_ignore(line):
                continue

            # ── Mode changes ──────────────────────────────────────
            if line == "SCAN_MODE":
                in_scan_mode = True
                print("[STATUS]  : ESP32 entered SCAN MODE - ready for attendance\n")
                continue

            if line == "CMD_MODE":
                in_scan_mode = False
                print("[STATUS]  : ESP32 entered COMMAND MODE\n")
                continue

            # ── System messages ───────────────────────────────────
            if line == "READY":
                print("[STATUS]  : ESP32 online and ready")
                continue

            if line.startswith("Sensor found"):
                print("[STATUS]  : Fingerprint sensor detected")
                continue

            if line.startswith("Stored fingerprints:"):
                print(f"[INFO]    : {line}")
                continue

            if line.startswith(">> ") or line.startswith("SUCCESS") or \
               line.startswith("Total stored") or line.startswith("Step"):
                print(f"[ESP32]   : {line}")
                continue

            # ── Scan results ──────────────────────────────────────
            if line.startswith("ID:"):
                current_id = int(line.split(":")[1])
                continue

            if line.startswith("CONFIDENCE:") and current_id is not None:
                confidence = int(line.split(":")[1])
                now        = datetime.now()
                status     = "GOOD MATCH" if confidence >= 100 else "WEAK MATCH"

                # Duplicate protection
                if current_id in last_scan:
                    elapsed = (now - last_scan[current_id]).total_seconds()
                    if elapsed < COOLDOWN_SECONDS:
                        print(f"[SKIP]    : ID:{current_id} scanned {elapsed:.1f}s ago (cooldown {COOLDOWN_SECONDS}s)\n")
                        current_id = None
                        continue

                last_scan[current_id] = now

                # Look up student
                student = get_student(conn, current_id)
                if student is None:
                    student = {
                        "student_no":   "N/A",
                        "student_name": f"Unknown ID:{current_id}",
                        "grade":        "N/A",
                        "section":      "N/A",
                    }
                    print(f"[WARN]    : ID {current_id} not in students table - logged as unknown\n")

                log_attendance(conn, current_id, confidence, status, now)

                print("─" * 48)
                print(f"  SCAN LOGGED")
                print("─" * 48)
                print(f"  Name         : {student['student_name']}")
                print(f"  Student No.  : {student['student_no']}")
                print(f"  Grade        : {student['grade']}")
                print(f"  Section      : {student['section']}")
                print(f"  Date         : {now.strftime('%Y-%m-%d')}")
                print(f"  Time         : {now.strftime('%H:%M:%S')}")
                print(f"  Confidence   : {confidence}")
                print(f"  Status       : {status}")
                print("─" * 48)
                print()

                current_id = None
                continue

            if line == "UNKNOWN":
                print("[SCAN]    : Finger not recognized - not enrolled\n")
                continue

            if line.startswith("LOW_CONFIDENCE:"):
                conf = line.split(":")[1]
                print(f"[SCAN]    : Weak match ignored (confidence: {conf}) - try again\n")
                continue

            # ── Anything else ─────────────────────────────────────
            if line:
                print(f"[ESP32]   : {line}")

    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C)")
    finally:
        stop_event.set()
        try:
            send_command(esp32, "STOP")  # Tell ESP32 to stop scanning cleanly
        except:
            pass
        esp32.close()
        conn.close()
        print("Connections closed. Goodbye.")


if __name__ == "__main__":
    main()