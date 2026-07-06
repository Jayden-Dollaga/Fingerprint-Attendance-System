###############################################################################
#  main.py
#  AS608 Fingerprint Attendance System
#
#  Entry point — ties all modules together.
#  Run this file to start the system.
#
#  Usage:
#    python main.py
#
#  Commands (type while running):
#    scan       Tell ESP32 to start scanning
#    stop       Tell ESP32 to stop scanning
#    list       Ask ESP32 how many fingers stored
#    enroll     Tell ESP32 to enroll using the next free ID
#    enroll:1   Tell ESP32 to enroll finger as ID 1
#    delete:1   Tell ESP32 to delete finger ID 1
#    wipe       Tell ESP32 to wipe all fingers
#    quit       Exit
###############################################################################

import sys
import time
import threading
from pathlib import Path

PYTHON_ROOT = Path(__file__).resolve().parent
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from config import COM_PORT, AUTO_SCAN
from core.database import init_database
from core.serial_handler import SerialHandler
from core.attendance import AttendanceProcessor
from core.commands import cmd_scan, cmd_stop, cmd_enroll, cmd_delete, cmd_wipe, cmd_list

try:
    from gui.app import main as gui_main
except ImportError:
    gui_main = None


# ==============================================================================
#  INPUT THREAD
# ==============================================================================

def input_thread(handler, stop_event):
    """Background thread — lets you type commands while scanning runs."""
    print("\nCommands: scan / stop / list / enroll:X / delete:X / wipe / quit\n")
    while not stop_event.is_set():
        try:
            cmd = input()
            if not cmd.strip():
                continue
            if cmd.strip().lower() == "quit":
                print("Exiting...")
                stop_event.set()
                break
            command = cmd.strip().lower()
            if command == "scan":
                sent = cmd_scan(handler)
            elif command == "stop":
                sent = cmd_stop(handler)
            elif command.startswith("enroll"):
                parts = command.split(":", 1)
                fingerprint_id = None
                if len(parts) == 2 and parts[1].isdigit():
                    fingerprint_id = int(parts[1])
                sent = cmd_enroll(handler, fingerprint_id)
            elif command.startswith("delete"):
                parts = command.split(":", 1)
                sent = False
                if len(parts) == 2 and parts[1].isdigit():
                    sent = cmd_delete(handler, int(parts[1]))
            elif command == "list":
                sent = cmd_list(handler)
            elif command == "wipe":
                sent = cmd_wipe(handler)
            else:
                sent = handler.send_command(cmd.strip())

            if sent:
                print(f"[SENT]    : {cmd.strip().upper()}")
            else:
                print("[ERROR]   : Not connected to ESP32")
        except EOFError:
            break


# ==============================================================================
#  MAIN
# ==============================================================================

def main():
    print("=" * 55)
    print("  AS608 Fingerprint Attendance System")
    print("=" * 55)

    # ── Init database ─────────────────────────────────────────────
    init_database()

    # ── Connect to ESP32 ─────────────────────────────────────────
    print(f"Port      : {COM_PORT}")
    handler = SerialHandler()
    ok, msg = handler.connect()

    if not ok:
        print(f"[ERROR]   : Could not connect to {COM_PORT}")
        print(f"Details   : {msg}")
        print("\nFixes:")
        print("  - Close Arduino Serial Monitor")
        print("  - Check ESP32 is plugged in")
        print("  - Check port in Arduino IDE -> Tools -> Port")
        return

    print("Status    : Connected!\n")

    # ── Auto-send SCAN ────────────────────────────────────────────
    if AUTO_SCAN:
        time.sleep(0.5)
        cmd_scan(handler)
        print("[SENT]    : SCAN\n")

    # ── Start input thread ────────────────────────────────────────
    stop_event = threading.Event()
    t = threading.Thread(
        target=input_thread,
        args=(handler, stop_event),
        daemon=True
    )
    t.start()

    # ── Processor ─────────────────────────────────────────────────
    processor   = AttendanceProcessor()
    in_scan_mode = False

    try:
        while not stop_event.is_set():
            line = handler.read_line()

            if line is None:
                time.sleep(0.05)
                continue

            if not line:
                continue

            # ── Mode messages ─────────────────────────────────────
            if line == "SCAN_MODE":
                in_scan_mode = True
                print("[STATUS]  : ESP32 in SCAN MODE — ready for attendance\n")
                continue

            if line == "CMD_MODE":
                in_scan_mode = False
                processor.reset()
                print("[STATUS]  : ESP32 in COMMAND MODE\n")
                continue

            # ── Ignore boot noise ─────────────────────────────────
            if handler.should_ignore(line):
                continue

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
               line.startswith("Total stored") or line.startswith("Step") or \
               line.startswith("---"):
                print(f"[ESP32]   : {line}")
                continue

            # ── Unknown / low confidence ──────────────────────────
            if line == "UNKNOWN":
                print("[SCAN]    : Finger not recognized\n")
                continue

            if line.startswith("LOW_CONFIDENCE:"):
                conf = line.split(":")[1]
                print(f"[SCAN]    : Weak match ignored (confidence: {conf})\n")
                continue

            # ── Scan processing ───────────────────────────────────
            result = processor.process_line(line)

            if result:
                if not result["logged"]:
                    print(f"[SKIP]    : ID:{result['fingerprint_id']} — {result['reason']}\n")
                else:
                    ts = result["timestamp"]
                    print("─" * 48)
                    print(f"  SCAN LOGGED")
                    print("─" * 48)
                    print(f"  ID           : {result['fingerprint_id']}")
                    print(f"  Date         : {ts.strftime('%Y-%m-%d')}")
                    print(f"  Time         : {ts.strftime('%H:%M:%S')}")
                    print(f"  Confidence   : {result['confidence']}")
                    print(f"  Status       : {result['status']}")
                    print("─" * 48)
                    print()
                continue

            # ── Anything else ─────────────────────────────────────
            if line:
                print(f"[ESP32]   : {line}")

    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C)")
    finally:
        stop_event.set()
        handler.disconnect()
        print("Connections closed. Goodbye.")


if __name__ == "__main__":
    if gui_main is not None:
        gui_main()
    else:
        main()
