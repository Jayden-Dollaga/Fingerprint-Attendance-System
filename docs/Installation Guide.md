# Installation Guide

## Overview

This guide covers the full setup path for installing and running the Fingerprint Attendance System on a Windows workstation. It includes dependency installation, firmware upload, hardware checks, and the recommended launch procedure.

## Requirements

Before starting, confirm that you have:

- Python 3.13 or newer installed
- Arduino IDE installed for uploading firmware
- a USB cable and a working ESP32 board
- the AS608 fingerprint sensor connected correctly

## Recommended setup on Windows

### 1. Open the project folder

Open a terminal in the project root so that the local scripts and data directories resolve correctly.

### 2. Create a virtual environment (optional but recommended)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```powershell
pip install -r requirements.txt
```

If the install is slow or fails, make sure you are using the Python environment that you intend to run the app from.

### 4. Upload the firmware

Open the Arduino sketch at firmware/ESP32_Fingerprint_AllInOne/ESP32_Fingerprint_AllInOne.ino in Arduino IDE and upload it to the ESP32.

Verify that:

- the correct board is selected
- the correct COM port is selected
- the firmware builds without errors

### 5. Connect the hardware

Connect the ESP32 to the PC through USB and ensure the fingerprint sensor is wired to the ESP32 according to the hardware guide.

### 6. Launch the application

You can run the app in either of these ways:

```powershell
python python/gui/app.py
```

or from the project root:

```powershell
python python/main.py
```

## Windows helpers

The repository includes convenience scripts for Windows users:

- install_requirements.bat for installing dependencies
- run_app.bat for launching the GUI

Double-clicking these from the project root is the fastest path for most users.

## Post-install verification

After launching the app, verify that:

- the ESP32 appears on a valid COM port
- the connection status becomes active
- enrollment and scan actions respond normally
- attendance data appears in the local database

## Common issues

### Serial port not found

- confirm the ESP32 is plugged in
- close the Arduino Serial Monitor if it is using the port
- choose the correct COM port in the GUI or settings

### Dependency installation fails

- make sure pip is using the correct Python runtime
- run the install again after upgrading pip

### Firmware upload fails

- check USB connections
- select the correct board profile
- ensure the selected serial port is free
