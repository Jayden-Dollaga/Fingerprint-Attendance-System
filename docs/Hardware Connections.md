# Hardware Connections

## Overview

The fingerprint attendance system uses an ESP32 board and an AS608 optical fingerprint sensor. The ESP32 acts as the controller and serial bridge, while the AS608 provides scanning and matching functionality.

## Recommended hardware

- ESP32 DevKit or WROOM-32 board
- AS608 fingerprint sensor module
- USB cable for power and serial communication
- breadboard and jumper wires
- stable 3.3V power source

## Default wiring

| AS608 pin | Connection | ESP32 connection |
| --- | --- | --- |
| V+ | 3.3V | 3.3V |
| GND | Ground | GND |
| TX | Sensor TX | ESP32 RX |
| RX | Sensor RX | ESP32 TX |

> The exact pin numbers may vary by board revision. The current firmware expects a serial-based communication path between the ESP32 and the sensor module.

## Notes on wiring quality

- use short, secure jumper connections
- keep the sensor away from power noise where possible
- avoid loose wires that can cause intermittent serial reads
- make sure the sensor board is powered from a stable source

## Serial considerations

The host machine connects to the ESP32 through USB. The Python application uses the discovered COM port to communicate with the device. If you change boards or wiring significantly, verify that the firmware and host-side serial settings still agree.

## Validation checklist

Before using the device, confirm that:

- the ESP32 powers on normally
- the sensor powers on and stays stable
- the USB cable is reliable
- the serial port appears in the operating system
- the firmware uploads successfully
