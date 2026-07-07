# Fingerprint Attendance System v2.0

**Status:** ✅ Production Ready — ESP32 fingerprint scanning, a desktop GUI, SQLite storage, backup/restore support, role-based access, and reporting.

This project began as a practical hardware experiment: connect a fingerprint sensor to an ESP32, read biometric input, and use a desktop application to manage attendance records. It has since grown into a complete attendance-management platform with embedded firmware, a Python application, a local database, and reporting tools.

---

## Table of Contents

- [What this project does](#what-this-project-does)
- [Project goals](#project-goals)
- [How the system works from the start](#how-the-system-works-from-the-start)
- [Hardware used](#hardware-used)
- [Software stack](#software-stack)
- [Project structure](#project-structure)
- [Installation and setup](#installation-and-setup)
- [Typical workflow](#typical-workflow)
- [ESP32 command reference](#esp32-command-reference)
- [Roles and permissions](#roles-and-permissions)
- [Database and data handling](#database-and-data-handling)
- [Automation and reliability](#automation-and-reliability)
- [Development notes and project evolution](#development-notes-and-project-evolution)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Version notes](#version-notes)

---

## Quick Start

The fastest way to try the GUI on Windows:

1. Install dependencies (one-time):

```bash
install_requirements.bat
```

1. Launch the desktop GUI:

```bash
run_app.bat
```

Command-line alternatives:

```bash
python -m pip install -r requirements.txt   # Optional
python python/gui/app.py                    # Run GUI directly
python python/main.py                       # Run console mode (serial CLI)
```

---

## What this project does

The system is designed for schools, offices, or training centers and supports:

- enroll students with fingerprint data
- scan fingerprints for attendance verification
- store attendance records with timestamps and confidence values
- manage student details in a local database
- view attendance analytics and reports
- back up and restore database snapshots
- restrict actions by user role
- communicate with a fingerprint sensor over serial using an ESP32

In short, it covers the full biometric attendance workflow from sensor input to data storage and reporting.

---

## Project goals

This project was designed to be:

- affordable and easy to build with common hardware
- modular so each layer can be maintained independently
- practical for real-world attendance use
- suitable for small to medium educational or organizational deployment
- extensible for future features such as cloud sync, RFID, or face recognition

---

## How the system works from the start

1. A student is enrolled through the GUI.
2. The Python application sends an enrollment command to the ESP32.
3. The ESP32 reads the fingerprint from the AS608 sensor and stores it internally.
4. The student profile is saved in the SQLite database.
5. Later, the user starts attendance mode.
6. The ESP32 waits for a fingerprint scan and identifies it if it matches a stored template.
7. The Python app logs the attendance event and saves it to the database.
8. The user can review logs, statistics, backups, and exports from the desktop interface.

This is the full lifecycle of the system, from hardware registration to attendance reporting.

---

## Hardware used

| Component | Purpose |
| --- | --- |
| ESP32 DevKit / WROOM-32 | Main controller and serial bridge |
| AS608 fingerprint sensor | Captures and matches fingerprints |
| USB cable | Connects the ESP32 to the computer |
| Breadboard and jumper wires | Wiring between the sensor and ESP32 |
| Windows PC | Runs the Python GUI and database logic |

### Typical wiring

| AS608 wire | Color | ESP32 connection |
| --- | --- | --- |
| V+ | Purple | 3.3V |
| GND | Blue | GND |
| TX | Orange | RX pin |
| RX | White | TX pin |

The exact GPIO mapping may vary depending on the firmware and hardware layout. The current firmware expects a serial-based connection between the ESP32 and the sensor module.

---

## Software stack

- Python 3.13+
- CustomTkinter for the desktop GUI
- PySerial for serial communication
- SQLite for local data storage
- Matplotlib for charts and reports
- OpenPyXL for Excel export
- Pillow for image-related helpers
- Arduino IDE for compiling and uploading firmware

---

## Project structure

```text
Fingerprint-Attendance-System/
├── firmware/                     # ESP32 Arduino sketches
│   ├── attendance/
│   ├── enroll/
│   ├── delete/
│   ├── test/
│   └── ESP32_Fingerprint_AllInOne/
├── python/
│   ├── main.py                   # Main entry point
│   ├── config.py                 # Serial, database, role, and behavior settings
│   ├── core/                     # Database, serial, attendance, command logic
│   ├── gui/                      # Desktop UI modules
│   └── services/                 # Backup and export helpers
├── data/                         # Database, backups, logs, exports
├── docs/                         # Project documentation
├── tests/                        # Validation and regression tests
├── requirements.txt              # Python dependencies
└── LICENSE
```

### Main Python modules

- [python/main.py](python/main.py) — startup entry point for the application
- [python/config.py](python/config.py) — central configuration for port detection, serial settings, roles, and defaults
- [python/core/serial_handler.py](python/core/serial_handler.py) — manages communication with the ESP32
- [python/core/database.py](python/core/database.py) — stores and queries attendance and student records
- [python/core/attendance.py](python/core/attendance.py) — processes scanned fingerprint events
- [python/core/commands.py](python/core/commands.py) — sends firmware commands like scan, enroll, delete, and wipe
- [python/gui/app.py](python/gui/app.py) — main GUI controller and page orchestrator
- [python/gui/attendance_page.py](python/gui/attendance_page.py) — attendance view and record rendering
- [python/gui/students_page.py](python/gui/students_page.py) — student registration and management UI
- [python/gui/dialogs.py](python/gui/dialogs.py) — enrollment, backup, restore, and wipe dialogs
- [python/gui/sidebar.py](python/gui/sidebar.py) — connection and quick-action controls

---

## Installation and setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Upload the firmware

Open the Arduino sketch in [firmware/ESP32_Fingerprint_AllInOne/ESP32_Fingerprint_AllInOne.ino](firmware/ESP32_Fingerprint_AllInOne/ESP32_Fingerprint_AllInOne.ino) and upload it to the ESP32 through the Arduino IDE.

### 3. Connect the hardware

Make sure the fingerprint sensor and ESP32 are wired correctly and that the serial connection is available.

### 4. Install dependencies (Windows)

Double-click [install_requirements.bat](install_requirements.bat) to install the Python dependencies.

### 5. Run the GUI application

Double-click [run_app.bat](run_app.bat) to launch the desktop GUI.

If you prefer the command line, you can also run:

```bash
python python/gui/app.py
```

> The GUI now opens larger by default so more of the interface fits on the screen.

---

## Typical workflow

### Enrollment

1. Open the app and connect to the ESP32.
2. Select the enrollment action.
3. Place a finger on the sensor.
4. Confirm the process in the GUI.
5. Enter or review student information.
6. Save the student profile to the database.

### Attendance scanning

1. Start scanning mode.
2. Place a registered finger on the sensor.
3. The ESP32 attempts to match the fingerprint.
4. If matched, the attendance event is stored.
5. The attendance view updates and the record becomes visible in the database.

### Data review and export

- open the attendance list
- inspect student records
- export data to Excel
- view charts and analytics
- create backups and restore previous versions if needed

---

## ESP32 command reference

| Command | Purpose |
| --- | --- |
| SCAN | Start attendance scanning mode |
| STOP | Exit scanning mode |
| ENROLL | Enroll a new fingerprint using the next available slot |
| ENROLL:1 | Enroll a fingerprint as a specific ID |
| DELETE:1 | Delete a specific fingerprint |
| WIPE | Remove all stored fingerprints |
| LIST | Show stored fingerprint count |

---

## Roles and permissions

The application supports role-based access so different users can work with different levels of control.

| Role | Permissions |
| --- | --- |
| Administrator | Full access including scan, enroll, delete, wipe, export, backup, and restore |
| Teacher | Scan, export, and backup access |
| Guest | Scan-only access |

The current role can be changed from the GUI and the available actions update immediately.

---

## Database and data handling

The system uses SQLite to store:

- student details
- fingerprint IDs
- attendance events
- timestamps and confidence values
- backup metadata

The database is stored under [data/attendance.db](data/attendance.db), and backup snapshots are stored under [data/backups](data/backups).

### Backup behavior

- backups are created as timestamped database snapshots
- previous backups can be restored from the GUI
- backups help protect against accidental data loss

---

## Automation and reliability

The current system includes:

- automatic serial port detection when possible
- reconnect logic for dropped serial connections
- cooldown handling to avoid duplicate attendance logging
- logging for operational visibility
- permission checks in the GUI so restricted actions are disabled for lower-privileged roles
- persistent user settings stored in a JSON file for COM port, baud rate, theme, cooldown, and auto-reconnect behavior
- type hints added to key database and serial helper functions to improve readability and editor support

### Settings persistence

The app now saves user preferences to [data/settings.json](data/settings.json) so the interface remembers your choices between sessions.

Saved settings include:

- COM port
- baud rate
- attendance cooldown
- theme mode
- auto-reconnect preference

These values are loaded automatically when the app starts and can be updated from the Settings dialog.

---

## Development notes and project evolution

This project has evolved in stages:

1. Initial prototype for fingerprint enrollment and scanning
2. Addition of a desktop GUI for easier operation
3. Integration with SQLite for persistent storage
4. Addition of charts, export, backup, and restore features
5. Refactoring of the GUI into modular page-based components for maintainability

The current GUI structure is organized around page modules instead of one large monolithic window file, which makes the code easier to understand and extend.

---

## Troubleshooting

If the app does not connect to the ESP32:

- confirm the ESP32 is powered and connected
- close the Arduino Serial Monitor if it is holding the COM port
- check that the correct serial port is selected
- verify the baud rate matches the firmware
- confirm the firmware was uploaded successfully

If fingerprint enrollment or scanning behaves unexpectedly:

- verify the sensor wiring
- check whether the ESP32 is still in the expected mode
- inspect the application log output
- test the firmware separately if needed

---

## License

This project is provided for educational and institutional use. Please review the license file for details.

---

## Version notes

- Current focus: maintainability, reliability, and a cleaner user experience
- The GUI has been reorganized into modular page-based components
- Serial device detection has been improved to prefer likely USB UART ports over unrelated devices
