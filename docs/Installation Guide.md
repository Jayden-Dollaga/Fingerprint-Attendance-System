Installation Guide
==================

Prerequisites
-------------
- Python 3.13+ installed on the host PC
- Arduino IDE (for flashing ESP32 firmware)
- USB cable connecting ESP32 to the PC

Steps (Windows)
---------------
1. Open a command prompt in the project root.
2. (Optional) Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

4. Configure serial port if needed by editing `python/config.py` (`COM_PORT`).
5. To run the app locally, run:

```powershell
python python/main.py
```

Running via helper (Windows)
---------------------------
- `run_app.bat` is provided for convenience; it installs dependencies (if missing) and launches the GUI when double-clicked.

Flashing ESP32
---------------
- Open `firmware/ESP32_Fingerprint_AllInOne/ESP32_Fingerprint_AllInOne.ino` in Arduino IDE, select the correct board/port, and upload.

Session Notes — 2026-07-05
-------------------------
- On Windows, the project now includes `run_app.bat` as a simple launcher that can install missing dependencies and start the GUI with a double click.
- For the latest experience, run the app from the project root so the bundled Python entry point and local data folders resolve correctly.
- The GUI now starts in a Today-focused attendance view by default, which makes the morning roll-call workflow more natural.
- Unknown fingerprint scans are now preserved in the attendance history and displayed as unregistered events in the UI.
- The app enforces valid positive fingerprint IDs for student registration, preventing sentinel ID `0` from becoming a student profile.

Notes
-----
- If dependency installation fails, make sure `pip` targets the Python installation chosen by your system.
- `pyserial` is required for serial; if missing the app will warn and fail serial operations.
