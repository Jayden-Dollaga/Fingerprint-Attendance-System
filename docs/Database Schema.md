Database Schema
===============

Overview
--------
The application uses SQLite for both student profile storage and attendance history. The schema is designed to support daily roll-call workflows, manual student registration, backup/restore operations, and reporting.

Core Tables
-----------

### students
Stores enrolled fingerprint profiles and their human-readable metadata.

```sql
CREATE TABLE students (
    fingerprint_id  INTEGER PRIMARY KEY,
    student_no      TEXT    NOT NULL UNIQUE,
    student_name    TEXT    NOT NULL,
    grade           TEXT    NOT NULL,
    section         TEXT    NOT NULL,
    enrollment_date TEXT    NOT NULL,
    updated_date    TEXT    NOT NULL
);
```

### attendance
Stores attendance events including matched scans and unregistered/unknown scans.

```sql
CREATE TABLE attendance (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint_id  INTEGER NOT NULL,
    date            TEXT    NOT NULL,
    time            TEXT    NOT NULL,
    confidence      INTEGER NOT NULL,
    status          TEXT    NOT NULL,
    timestamp       TEXT    NOT NULL
);
```

Operational Notes
-----------------
- Fingerprint ID `0` is used as a sentinel value for unknown/unregistered scans and is displayed in the UI as "Unregistered".
- Attendance rows are preserved for history, reports, and auditing even when no roster record exists for the scan.
- Indexes and helper queries are used to support day-based views and paginated history browsing.

Session Update — 2026-07-05
--------------------------

- The `attendance` table continues to store both recognized scans and unknown scans using the same normalized event model.
- Unknown scans are now intentionally persisted with `fingerprint_id = 0` and `status = "UNKNOWN"`, which allows the GUI to distinguish them as sentinel unregistered events.
- The `students` table is protected from having fingerprint ID `0` inserted, preserving sentinel behavior and preventing confusion between unknown scans and real student profiles.
- The application now avoids registering student profiles for sentinel IDs and instead requires a valid positive fingerprint ID before `register_student()` will succeed.
