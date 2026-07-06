Hardware Connections
=====================

Supported Hardware
------------------
- ESP32 WROOM-32 (USB serial)
- AS608 Optical Fingerprint Sensor
- USB cable for serial

Default Pin Mapping (ESP32)
---------------------------
- AS608 TX -> ESP32 RX (GPIO 14)  
- AS608 RX -> ESP32 TX (GPIO 27)  
- VCC -> 3.3V
- GND -> GND

Notes
-----
- The firmware expects the serial port to be available over USB. Configure `COM_PORT` in `python/config.py` when deploying to another machine.
- Use a stable power source for the sensor to prevent false reads.
- If using a different ESP32 board or different pins, update the firmware pins and ensure `BAUD_RATE` matches `python/config.py`.

Session Notes — 2026-07-05
-------------------------

- No hardware wiring changes were made during this session. The work focused on the Python GUI, SQLite attendance data model, and serial command handling.
