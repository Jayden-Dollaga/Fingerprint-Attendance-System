# Wiring Guide

## ESP32 to AS608

- V+ -> 3.3V
- GND -> GND
- TX -> GPIO 14
- RX -> GPIO 27

## Notes

- Use the same baud rate configured in python/config.py.
- If serial communication is unstable, check cable grounding and power.
