Change Log
==========

v2.3 — 2026-07-05
-----------------
- Add: Windows launcher for one-click startup and dependency setup via `run_app.bat`.
- UI: Reworked the Attendance view into a Today-first experience with clearer cards, status badges, confidence indicators, and a secondary Recent/Load More history path.
- Add: Unknown or unregistered scans now appear as red unregistered entries in the attendance UI, are saved to attendance history, and do not create student roster rows by default.
- Fix: Added cooldown/rate-limiting for repeated UNKNOWN scans and switched to incremental attendance card rendering for better performance as history grows.
- Fix: Added ID/CONFIDENCE timeout protection so stale fingerprint IDs expire before the next confidence reading.
- Improve: New scans now insert cards into the active Attendance tab only when that tab is visible, avoiding unnecessary full refreshes.
- Add: Added an Add Student dialog for unregistered scans so admins can register a student profile manually from the attendance view.
- Fix: Hardened reconnect, restore, and permission flows with safer dialogs, stop-before-restore protection, and more reliable UI state updates.
- Docs: Added a detailed implementation and session summary across the documentation set.

Detailed Session Summary
------------------------
- Enforced "Today" as the default attendance view on startup, while preserving a secondary "Recent" history mode with pagination.
- Fixed attendance ordering so newest records render first and recent scans are inserted at the top of the current view.
- Preserved and rendered UNKNOWN/unregistered fingerprint scans as real history entries using `fingerprint_id = 0`.
- Guaranteed that unregistered scans are saved to the attendance table and displayed as red "Unregistered" cards rather than being dropped.
- Added per-fingerprint cooldown tracking so duplicate scans are blocked independently for each fingerprint ID.
- Fixed the scan parser to use a dedicated `last_logged_times` dictionary rather than a single global scan state, preventing different fingerprints from bypassing duplicate protection.
- Prevented the Add Student flow from accepting sentinel fingerprint ID `0`, making it available only for real registered fingerprint IDs.
- Hardened the registration path to stop student rows from being created for unknown scans and to keep the sentinel `0` behavior consistent.
- Fixed startup refresh/load-more interaction by ensuring the attendance list and load-more button exist before visibility logic runs.
- Updated the GUI refresh pipeline so Today mode resets pagination, Recent mode loads pages consistently, and card metadata is rebuilt from fresh student lookup.
- Verified the behavior with `python -m py_compile` and a unit test for attendance parsing.

v2.2 — 2026-07-05
-----------------

- Fix: Hardened serial auto-reconnect loop and GUI status updates during reconnect attempts.
- Add: `Restore DB` dialog in GUI to browse and restore timestamped backups (role-restricted).
- Fix: Enforced `export` permission in report viewing and export handlers.
- UI: Connection controls reliably reflect background reconnection progress.

v2.1 — 2026-07-04
-----------------

- Add: GUI Role Selector with live role switching
- Add: Auto-Attendance Logging with cooldown and confidence thresholds
- Fix: Wipe now clears both student profiles and attendance history
- Update: Default role set to `admin` for first-run convenience

v1.0 — Initial release
-----------------------

- Core firmware for ESP32 + AS608 fingerprint sensor
- Python GUI with basic enroll/scan/delete flows
- SQLite-backed persistence and basic report generation

Notes
-----
