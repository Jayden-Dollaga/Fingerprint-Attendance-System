# Project Overview

## Project name

AI-Assisted Fingerprint Attendance System

## Status

Production-ready prototype with ESP32 firmware, a Python desktop interface, SQLite storage, backup/restore support, reporting, and role-based access.

## Purpose

This project was built to automate attendance tracking using fingerprint recognition. Instead of relying on manual sign-in sheets, it uses a biometric sensor connected to an ESP32 and a desktop application that records attendance events and manages student data.

## What the system does

The system supports the full attendance lifecycle:

1. enroll a student and link a fingerprint template to that student
2. connect the desktop application to the ESP32 over serial
3. place a finger on the sensor to verify identity
4. record attendance events with time and confidence data
5. review records, generate reports, and export data
6. maintain backup copies of the database

## Hardware

| Component | Role |
| --- | --- |
| ESP32 | Main controller and serial bridge |
| AS608 fingerprint sensor | Reads and verifies fingerprint templates |
| Breadboard and jumper wires | Connect the sensor to the ESP32 |
| USB cable | Power and serial communication |
| Windows PC | Runs the Python application and database |

## Software stack

- Python 3.13+
- CustomTkinter for the GUI
- PySerial for serial communication
- SQLite for local persistence
- Matplotlib for charts
- OpenPyXL for Excel export
- Pillow for supporting image-related helpers
- Arduino IDE for firmware development

## Repository structure

```text
AI-Assisted Fingerprint Attendance System/
├── firmware/                  # ESP32 sketches
├── python/                    # Python backend and GUI
├── data/                      # SQLite database, logs, exports, backups
├── docs/                      # Documentation
├── tests/                     # Validation and regression tests
├── requirements.txt           # Python dependencies
└── README.md                  # Main project entry point
```

## Core architecture

The application is split into clear layers:

- firmware layer: the sketch running on the ESP32
- communication layer: serial commands and responses
- application layer: Python logic for handling attendance and student operations
- presentation layer: the desktop GUI with separate page modules
- persistence layer: SQLite database and backup files

## Main workflow

### Enrollment flow

1. The user opens the GUI and connects to the ESP32.
2. The user starts enrollment mode.
3. The ESP32 captures a fingerprint template.
4. The Python app saves the student profile and links it to the fingerprint ID.

### Attendance flow

1. The user starts scanning mode.
2. A finger is placed on the sensor.
3. The ESP32 compares the input fingerprint to stored templates.
4. If matched, the Python app logs the attendance event.
5. The attendance list and reports update automatically.

## GUI modules

The GUI has been organized into focused modules so the code is easier to maintain:

- app.py: main controller and application lifecycle
- attendance_page.py: attendance records and display logic
- students_page.py: student registration and management
- dialogs.py: enrollment, backup, restore, and wipe dialogs
- sidebar.py: connection controls and quick actions
- statistics_page.py, reports_page.py, log_page.py: reporting and logging views

## Data handling

The application stores:

- student details
- fingerprint IDs
- attendance events
- timestamps and confidence scores
- backup snapshots

The SQLite database lives in the data directory and is used as the system’s primary persistent store.

## Configuration

Key settings are centralized in [python/config.py](python/config.py), including:

- serial port detection
- baud rate
- cooldown behavior
- role definitions
- backup and logging options

## Reliability features

The current system includes:

- serial reconnect handling
- role-based permissions in the GUI
- backup creation and restore support
- log output for troubleshooting and operational visibility
- automatic attendance logging with cooldown protection
- persistent settings stored locally so COM port, baud rate, theme, cooldown, and auto-reconnect preferences are restored automatically
- type hints on core database and serial communication helpers to improve maintainability and IDE feedback

## Getting started

1. Install the Python dependencies with [install_requirements.bat](../install_requirements.bat) or pip.
2. Upload the firmware to the ESP32.
3. Connect the hardware.
4. Launch the GUI with [run_app.bat](../run_app.bat) or python [python/gui/app.py](../python/gui/app.py).
5. Enroll students and begin scanning.

> The GUI now opens larger by default so more of the user interface is visible on start.

## Notes for future development

This project is a strong base for further expansion, including:

- cloud sync
- web-based dashboards
- multi-device support
- RFID or card-based fallback
- improved reporting and analytics

## Maintenance note

The project is intended to stay easy to maintain as it grows. Future work should focus on stronger testing, cleaner error handling, more reliable backup workflows, and better user-facing reporting.
