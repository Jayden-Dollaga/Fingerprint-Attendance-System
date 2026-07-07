# Database Schema

## Overview

The application uses SQLite as its local persistence layer. The schema is intentionally simple so that attendance events and student records can be reviewed quickly without requiring a separate database server.

## Tables

### students

The students table stores the main enrollment profile for each person.

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

The attendance table stores attendance events, including recognized and unknown scans.

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

## Design notes

- Fingerprint ID 0 is used as a sentinel value for unknown or unregistered scans.
- Attendance history is preserved even when no matching student record exists.
- The database is used for both operational history and reporting.

## Backup behavior

Backups are stored as timestamped database snapshots inside the data/backups directory. This provides a simple restore path if files are deleted, corrupted, or need to be rolled back.

## Data integrity considerations

- student IDs should remain unique and positive
- attendance events should be written with valid timestamps
- destructive actions should be used deliberately because they affect the local history store
