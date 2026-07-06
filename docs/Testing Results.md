Testing Results
===============

Summary
-------
- Several unit tests were added to validate core behaviors:
  - `tests/test_database_reset.py` — verifies `clear_all_data()` clears students and attendance
  - `tests/test_attendance_ui_utils.py` — validates attendance formatting helpers
- These tests pass in the current workspace and were used to validate the wipe and UI formatting changes.

How to run
----------
1. Ensure project dependencies are installed.
2. From the project root run:

```bash
pytest -q
```

Session Validation — 2026-07-05
-----------------------------
- Verified `python/gui/app.py` and `python/core/database.py` compile cleanly with `python -m py_compile`.
- Ran `python -m unittest -v tests.test_attendance_parsing` successfully to confirm the attendance parsing and scanning flow behaves correctly.
- Manual validation targeted the Today-default attendance workflow, unknown scan persistence, incremental card insertion, and the Add Student dialog gating.
- Confirmed that unknown scans are persisted in the DB as sentinel `fingerprint_id = 0` events and displayed correctly in the GUI.
- Confirmed that Add Student dialog gating now rejects invalid IDs and does not create student entries for unknown scans.
- Updated tests and documentation notes to reflect the new sentinel handling and per-fingerprint cooldown behavior.

Notes
-----

- Serial-dependent flows are not fully testable in CI without an attached ESP32. Tests focus on DB logic and UI helpers.
- Additional integration tests should be added to exercise backup/restore and reconnect behaviors (requires mocking serial or a virtual serial device).
