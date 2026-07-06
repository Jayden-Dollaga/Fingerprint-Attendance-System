# AI-Assisted Fingerprint Attendance System

**Status:** ✅ **Production Ready v2.2** — ESP32 Fingerprint Sensor + Python Backend + SQLite Database + CustomTkinter GUI + Charts + Backups + Role-Based Access + Auto-Logging

An enterprise-grade biometric attendance system using the AS608 fingerprint sensor, 
with a Python backend, SQLite database, CustomTkinter GUI, statistical charts, 
automatic backups, and role-based access control.

---

## Key Features

✅ **Fingerprint Enrollment & Scanning** — Add and authenticate students via fingerprint  
✅ **Attendance Tracking** — Automatic logging with timestamps and confidence scores  
✅ **Statistical Charts** — Attendance timeline, section distribution, grade analysis  
✅ **Database Backups** — Automatic timestamped backups with restore functionality  
✅ **User Roles** — Admin, Teacher, Guest roles with live GUI role selector  
✅ **Auto-Attendance Logging** — Automatic database saves on fingerprint matches (2s cooldown)  
✅ **Auto-Reconnect** — Exponential backoff reconnection on connection loss  
✅ **Centralized Logging** — Daily log files with multiple log levels  
✅ **Excel Export** — Export attendance records to spreadsheet format  
✅ **Dark Mode UI** — Modern CustomTkinter interface with professional styling  

---

## Hardware

| Component | Details |
|---|---|
| Microcontroller | ESP32 WROOM-32 with Screw Terminal Shield |
| Fingerprint Sensor | AS608 Optical Fingerprint Sensor |
| Connection | USB Serial (COM5 default) |

### Wiring

| AS608 Wire | Color | Shield Terminal |
|---|---|---|
| V+ | Purple | V column |
| GND | Blue | G column |
| TX | Orange | S column, D14 row |
| RX | White | S column, D27 row |

---

## Project Structure

```
AI-Assisted-Fingerprint-Attendance-System/
├── firmware/                   # Arduino sketch for ESP32
├── python/
│   ├── main.py                 # Entry point
│   ├── fix_emoji.py            # Small helper to restore the statistics tab emoji
│   ├── config.py               # Settings + user roles
│   ├── core/
│   │   ├── serial_handler.py   # Serial I/O + auto-reconnect
│   │   ├── commands.py         # Command abstraction
│   │   ├── database.py         # SQLite + charts + backups
│   │   ├── attendance.py       # Attendance processing
│   │   ├── logger.py           # Centralized logging
│   │   └── utils.py            # Utilities
│   ├── gui/                    # CustomTkinter GUI with role-based access
│   └── services/               # Excel export, backup
├── data/
│   ├── attendance.db           # SQLite database
│   ├── backups/                # Timestamped backup files
│   ├── charts/                 # Generated attendance charts
│   └── logs/                   # Daily log files
├── tests/                      # Comprehensive tests
├── docs/                       # Detailed architecture docs
└── requirements.txt            # Python dependencies
```

---

## Quick Start

### 1. Flash ESP32

Open [firmware/ESP32_Fingerprint_AllInOne/ESP32_Fingerprint_AllInOne.ino](firmware/ESP32_Fingerprint_AllInOne/ESP32_Fingerprint_AllInOne.ino)
in Arduino IDE and upload to your ESP32.

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `pyserial==3.5` — Serial communication
- `customtkinter==6.0.0` — Modern GUI
- `openpyxl==3.1.5` — Excel export
- `matplotlib==3.8.4` — Chart generation
- `Pillow==10.1.0` — Image processing

### 3. Configure COM port (optional)

Edit [python/config.py](python/config.py):
```python
COM_PORT = "COM5"   # Change to your ESP32 port
```

### 4. Run the application

On Windows, you can double-click [run_app.bat](run_app.bat) to install dependencies and launch the app automatically.

```bash
python python/main.py
```

This launches the CustomTkinter GUI with all features.

### 5. Basic workflow

1. **Select Role** — Use the role dropdown (top-right) to choose between Admin, Teacher, or Guest
2. **Connect** — Click "Connect" button to establish serial connection with ESP32
3. **Enroll** — Click "Enroll" to register a new fingerprint with student profile
4. **Scan** — Click "Start Scan" to begin attendance mode (auto-saves to database)
5. **View Stats** — Click "Statistics" tab to see charts and analytics
6. **Backup** — Click "Backup" button to create database backup (if your role allows)

---

## ESP32 Firmware Commands

| Command | Action |
|---|---|
| `SCAN` | Start attendance scan mode |
| `STOP` | Return to command mode |
| `ENROLL` | Enroll finger with auto-assigned ID |
| `ENROLL:1` | Enroll finger as specific ID |
| `DELETE:1` | Delete finger ID 1 |
| `WIPE` | Delete all fingerprints |
| `LIST` | Show stored fingerprint count |

---

## User Roles & Permissions

The system includes three built-in roles with a **live GUI role selector** in the top-right corner:

| Role | Permissions | Use Case |
|---|---|---|
| **Admin** | Scan, Enroll, Delete, Wipe, Export, Backup, Restore | System administrator (default) |
| **Teacher** | Scan, Export, Backup | Teacher/Faculty — limited modifications |
| **Guest** | Scan only | Visitor/Read-only access |

**To change roles:** Use the dropdown selector in the top-right corner of the application. Buttons automatically enable/disable based on your role.

Permissions are automatically enforced in the GUI—buttons enable/disable based on the current role.

---

## Database Backups

The system automatically maintains timestamped backups:

- **Location:** `data/backups/attendance_YYYYMMDD_HHMMSS.db`
- **Automatic Creation:** Backup button in GUI (role-restricted)
- **Restore:** View and restore from any previous backup
- **Metadata:** Backup list shows timestamp, file size, and creation date

---

## Statistics & Charts

The Statistics tab displays three charts:

1. **Attendance Timeline** — Line chart of attendance records over 30 days
2. **Section Distribution** — Bar chart of student count per section
3. **Grade Distribution** — Pie chart of attendance by grade

Charts are saved to `data/charts/` and auto-update when new records are logged.

---

## Auto-Reconnect & Logging

- **Auto-Reconnect:** Automatic reconnection with exponential backoff (2s, 4s, 8s...)
- **Logging:** All events logged to `data/logs/YYYY-MM-DD.log`
- **Log Levels:** DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL with color coding
- **Guide:** See [docs/logging-guide.md](docs/logging-guide.md) for a practical overview of the logging system

---

## Moving to Another PC

1. Copy the entire project folder
2. Install Python 3.13+
3. Run `pip install -r requirements.txt`
4. Update `COM_PORT` in `python/config.py`
5. Run `python python/main.py`

The database (`data/attendance.db`) and backups (`data/backups/`) carry all data.
Copy these directories to preserve records on the new system.

---

## Current Status

This repository is **production-ready** and contains:

✅ Working ESP32 firmware for fingerprint enrollment and scanning  
✅ Python backend with serial communication and database operations  
✅ SQLite database for student and attendance records  
✅ Full-featured CustomTkinter GUI with role-based access  
✅ Statistical charts and analytics  
✅ Automatic database backups and restore functionality  
✅ User role system with permission enforcement  
✅ Auto-reconnect with exponential backoff  
✅ Centralized logging system  
✅ Excel export functionality  
✅ Comprehensive test suite  

---

## Built With

- **Microcontroller:** ESP32 WROOM-32
- **Sensor:** AS608 Fingerprint Sensor
- **Language:** Python 3.13+
- **GUI:** CustomTkinter 6.0.0
- **Database:** SQLite3
- **Libraries:** 
  - `pyserial` — Serial communication
  - `openpyxl` — Excel generation
  - `matplotlib` — Charts
  - `Pillow` — Image processing

---

## License

This project is provided as-is for educational and institutional use.

---

### Recent Updates (v2.2)

- ✅ **Reconnect Fix** — The serial reader and auto-reconnect loop were hardened so the app now continually retries with exponential backoff and updates the GUI status during reconnect attempts.
- ✅ **Restore UI** — Added a `Restore DB` dialog in the sidebar that lists timestamped backups and allows restoring a selected backup (role-restricted).
- ✅ **Permission Enforcement** — Viewing and exporting statistics now check the `export` permission at runtime; report buttons are disabled when the role lacks export rights.
- ✅ **Wipe Behavior** — Wipe clears both student profiles and attendance history (retained from v2.1).
- ✅ **Minor UI/UX** — Connection status and control buttons now reflect reconnect progress and final connection state more reliably.

### Author

Enforcer X — Research & Development  
**Last Updated:** July 5, 2026  
**Version:** 2.2 (Integration fixes: reconnect, restore UI, permissions)
