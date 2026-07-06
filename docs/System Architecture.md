System Architecture
===================

Overview
--------
This project implements a fingerprint-based attendance system that integrates the following major components:

- ESP32 microcontroller running Arduino firmware that talks to an AS608 fingerprint sensor.
- Python desktop application (CustomTkinter GUI) that communicates with the ESP32 over USB serial.
- SQLite database storing student profiles and attendance records.
- Backup/restore system that manages timestamped copies of the SQLite database.
- Role-based access control in the GUI to restrict actions (enroll, delete, wipe, export, backup, restore).

High-level Components
---------------------
- firmware/ESP32_Fingerprint_AllInOne: Arduino sketch implementing commands (SCAN/STOP/ENROLL/DELETE/WIPE/LIST) and sending structured lines over serial.
- python/main.py: Entry point for the GUI application.
- python/gui/app.py: CustomTkinter GUI, role selector, tabs (Attendance, Students, Statistics, Logs) and the connection UI.
- python/core/serial_handler.py: Encapsulates serial I/O, reading lines, and auto-reconnect with exponential backoff.
- python/core/database.py: SQLite access layer, CRUD for students, attendance logging, backup/restore utilities, report generation and chart helpers.
- python/core/commands.py: High-level commands sent to ESP32 (cmd_scan, cmd_stop, cmd_enroll, cmd_delete, cmd_wipe, cmd_list).
- python/core/logger.py: Centralized logging wrapper used across modules.
- python/services: Export & backup helpers (Excel export, wrappers around DB backup).

Data Flow
---------
1. User clicks "Connect" in GUI -> `SerialHandler.connect()` opens serial port and spawns a reader thread.
2. `read_serial_output()` loops and consumes lines from `SerialHandler.read_line()`.
3. Recognized events (ENROLLING, SUCCESS, ID messages) update dialog state and may call database functions.
4. Attendance events (ID messages with confidence) trigger `log_attendance()` which writes attendance rows into SQLite.
5. Backups are created by `backup_database()` (timestamped copies in `data/backups`) and can be restored via `restore_database()`.
6. Permission checks are centralized in the GUI (`has_permission()`) and enforced both in UI control states and in handlers.

Auto-Reconnect Behavior
-----------------------
- `SerialHandler` implements `auto_reconnect()` with exponential backoff (configured in `python/config.py` with `RECONNECT_BASE_DELAY` and `RECONNECT_MAX_RETRIES`).
- GUI's reader thread observes `serial_handler.reconnect_count` and updates status text to show progress (e.g. "Reconnecting... (2/5)").
- After a successful reconnect the GUI refreshes connection-related controls and resumes normal processing.

Files Map
---------
- `firmware/ESP32_Fingerprint_AllInOne/ESP32_Fingerprint_AllInOne.ino` — firmware entrypoint
- `python/main.py` — starts the app and handles top-level lifecycle
- `python/gui/app.py` — GUI + dialogs + business interactions
- `python/core/serial_handler.py` — serial I/O + reconnect
- `python/core/database.py` — DB schema, CRUD, backup/restore
- `python/core/commands.py` — mapping of high-level actions to serial commands
- `python/core/logger.py` — logging utility

Notes
-----
- The system aims to keep UI state consistent with background serial activity; recent fixes (v2.2) improve reconnect UI and guarantee the reader thread continues attempting reconnects until `RECONNECT_MAX_RETRIES`.
- Role-based permissions are enforced at both UI and handler levels for critical operations (export, restore, wipe, delete).

Recent Session Improvements
---------------------------

- Default attendance flow now opens in Today mode and preserves Recent history as a paginated secondary path.
- Live scan parsing now logs both recognized fingerprint matches and unknown scans into the attendance history.
- Unknown scans are persisted using sentinel `fingerprint_id = 0` and displayed as unregistered cards in the UI.
- Attendance refresh now rebuilds cards from fresh student profile joins, improving metadata accuracy after new registrations.
- Added stale `ID:` expiration and incremental Attendance tab updates that only occur when the Attendance view is active.
- UI and restore/workflow flows were hardened to prevent destructive actions during active scanning and to maintain state consistency.
