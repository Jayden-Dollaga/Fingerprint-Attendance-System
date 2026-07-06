Software Flow
=============

Startup
-------
- `python/main.py` initializes logging and the GUI application (`FingerprintApp`).
- Database is initialised via `init_database()` (creates tables if missing).

Connection Lifecycle
--------------------
- User clicks Connect -> `SerialHandler.connect()` opens serial port and returns status.
- On connect, the GUI starts a background reader thread (`read_serial_output`) that continuously calls `SerialHandler.read_line()`.
- If the serial handler reports a disconnect, `auto_reconnect()` uses exponential backoff to retry; the GUI observes `reconnect_count` to display progress and updates buttons accordingly.

Enrollment Flow
---------------
1. User clicks `Enroll` in GUI (permission checked).
2. GUI sends `ENROLL` command using `cmd_enroll()` and opens the enroll dialog.
3. The enroll dialog waits for ESP32 messages (`ENROLLING FINGER AS ID #n`, `SUCCESS! Finger saved as ID #n`) and enables Save when complete.
4. Saving registers the student in the `students` table via `register_student()`.

Scanning / Attendance
---------------------
- `cmd_scan()` instructs ESP32 to enter scan mode.
- ESP32 prints `ID: <n>` lines for recognized fingerprints; GUI parses these, applies cooldown rules, and calls `log_attendance()`.
- The parser now expires stale `ID:` state after a short timeout if no `CONFIDENCE:` line arrives.
- Attendance rows are inserted into the `attendance` table with timestamp and confidence.
- New scans are inserted incrementally into the active Attendance view rather than rebuilding the full list on every scan.

Roster Management
-----------------
- GUI provides a Students dialog listing profiles coming from `get_all_students()`.
- Delete flows send `DELETE:<id>` to the ESP32 (if connected) and remove the DB row locally; if disconnected, delete only updates DB and instructs user to re-run delete while connected to clear sensor.

Backup & Restore
----------------
- Backup: `backup_database()` copies the DB to `data/backups/attendance_YYYYMMDD_HHMMSS.db`.
- Restore UI lists these backups (`list_backups()`), and `restore_database(path)` replaces the active DB file with the chosen backup.
- After restore the GUI reloads DB state and refreshes roster/attendance UI.

Permissions
-----------
- `has_permission()` checks `python/config.py` `USER_ROLES` for the current role.
- UI controls render disabled/enabled states; critical handlers also enforce permission checks (e.g., export, restore, delete, wipe).

Logging
-------
- Application logs all notable events through `core.logger` to both console and files under `data/logs/`.
- Recent updates added clearer logging for reconnect attempts, backup success/failure, and restore operations.

Session Update — 2026-07-05
--------------------------

- The app now defaults to the Today attendance view and preserves Recent as a paged history mode.
- Matching fingerprint scans are logged immediately and inserted into the UI at the top when the current view is active.
- Unknown scans are recorded in the database as `fingerprint_id = 0` and rendered as "Unregistered" entries rather than being discarded.
- Added per-fingerprint cooldown enforcement, which prevents duplicate entries for the same fingerprint while still allowing different IDs to log normally.
- The scan parser now tracks `last_logged_times` per fingerprint ID and uses the same timeout logic for UNKNOWN scans through sentinel ID `0`.
- The attendance refresh flow now rebuilds the view cleanly from the database, resets pagination when switching back to Today, and preserves Recent history state correctly.
- Restore and wipe flows now verify that no active scan is in progress before executing destructive operations.
- This session included fixes to the attendance card rendering path so student metadata is recomputed from the latest roster state and stale Add Student actions are avoided.
