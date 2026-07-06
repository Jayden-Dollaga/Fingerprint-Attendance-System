# Architecture

The system is split into three layers:

1. Firmware layer: the ESP32 sketch reads fingerprint data and responds to serial commands.
2. Python backend: serial communication, attendance processing, and database handling run in the Python package.
3. Optional GUI layer: a Tkinter-based interface can be expanded for student management and settings.
