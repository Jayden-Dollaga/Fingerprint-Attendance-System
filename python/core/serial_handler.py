###############################################################################
#  serial_handler.py
#  AS608 Fingerprint Attendance System
#
#  All ESP32 serial communication lives here.
#  No database code, no business logic — just read and send.
###############################################################################

import time
import threading
from typing import Optional, List, Tuple

try:
    import serial
    from serial.tools import list_ports
except ModuleNotFoundError:  # pragma: no cover
    serial = None
    list_ports = None

from config import COM_PORT, BAUD_RATE, IGNORE_PREFIXES, AUTO_RECONNECT, RECONNECT_MAX_RETRIES, RECONNECT_BASE_DELAY
from core.logger import log


def list_serial_ports() -> List[str]:
    """Return a list of available serial port names."""
    if serial is None or list_ports is None:
        return []
    try:
        return [port.device for port in list_ports.comports()]
    except Exception:
        return []


class SerialHandler:
    def __init__(self) -> None:
        self.esp32                 = None
        self.connected             = False
        self.reconnect_count       = 0  # Track reconnection attempts
        self.reconnect_port: Optional[str] = None  # Remember port for auto-reconnect
        self.reconnect_baud: Optional[int] = None  # Remember baud for auto-reconnect
        self.auto_reconnect_enabled = AUTO_RECONNECT

    def list_available_ports(self) -> List[str]:
        return list_serial_ports()

    def connect(self, port: str = COM_PORT, baud: int = BAUD_RATE) -> Tuple[bool, str]:
        """
        Connect to ESP32 over serial.
        Returns (True, "OK") or (False, error message).
        """
        if serial is None:
            self.connected = False
            log.error("pyserial not installed — run: pip install -r requirements.txt")
            return False, "pyserial is not installed. Run: pip install -r requirements.txt"

        try:
            self.esp32     = serial.Serial(port, baud, timeout=1)
            time.sleep(2)  # Wait for ESP32 to boot after serial connects
            self.connected = True
            self.reconnect_port = port  # Save for auto-reconnect
            self.reconnect_baud = baud  # Save for auto-reconnect
            self.reconnect_count = 0  # Reset reconnect counter on successful connection
            log.success(f"Connected to {port} @ {baud} baud")
            return True, "OK"
        except serial.SerialException as e:
            self.connected = False
            log.error(f"Serial connection failed — {e}")
            return False, str(e)

    def disconnect(self) -> None:
        """Close serial connection cleanly."""
        if self.esp32 and self.esp32.is_open:
            try:
                self.send_command("STOP")
            except:
                pass
            self.esp32.close()
        self.connected = False
        log.info("Disconnected from ESP32")

    def send_command(self, cmd: str) -> bool:
        """
        Send a command string to the ESP32.
        Commands are uppercased automatically.
        Returns True if sent, False if not connected or on failure.
        """
        if not self.connected or not self.esp32:
            return False
        try:
            self.esp32.write((cmd.upper() + "\n").encode("utf-8"))
            return True
        except Exception as e:
            log.error(f"Failed to send command '{cmd}' to ESP32: {e}")
            self.connected = False
            return False

    def read_line(self) -> Optional[str]:
        """
        Read one line from ESP32.
        Returns decoded string or None if nothing available / decode error.
        Auto-reconnects if connection is lost.
        """
        if not self.connected or not self.esp32:
            if self.auto_reconnect_enabled and self.reconnect_port:
                self.auto_reconnect()
            return None
        
        # Check if port is still open
        if not self.esp32.is_open:
            self.connected = False
            log.warning("Serial port closed unexpectedly")
            if self.auto_reconnect_enabled:
                self.auto_reconnect()
            return None
        
        if self.esp32.in_waiting == 0:
            return None
        try:
            raw = self.esp32.readline()
            return raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            return None
        except Exception as e:
            log.error(f"Serial read error: {e}")
            self.connected = False
            if self.auto_reconnect_enabled:
                self.auto_reconnect()
            return None

    def should_ignore(self, line: str) -> bool:
        """Returns True for boot noise and ESP32 help text."""
        for prefix in IGNORE_PREFIXES:
            if line.startswith(prefix):
                return True
        return False

    def is_connected(self) -> bool:
        return bool(self.connected and self.esp32 and self.esp32.is_open)

    def auto_reconnect(self) -> bool:
        """
        Attempt to reconnect to ESP32 with exponential backoff.
        Used internally when connection is lost.
        """
        if not self.auto_reconnect_enabled or not self.reconnect_port:
            return False
        
        if self.reconnect_count >= RECONNECT_MAX_RETRIES:
            log.error(f"Auto-reconnect failed after {RECONNECT_MAX_RETRIES} attempts")
            return False
        
        # Calculate exponential backoff delay
        delay = RECONNECT_BASE_DELAY * (2 ** self.reconnect_count)
        self.reconnect_count += 1
        
        log.warning(f"Attempting reconnect ({self.reconnect_count}/{RECONNECT_MAX_RETRIES}) in {delay}s...")
        time.sleep(delay)
        
        # Try to reconnect
        success, msg = self.connect(self.reconnect_port, self.reconnect_baud)
        if success:
            log.success(f"Auto-reconnect successful")
            return True
        else:
            log.warning(f"Auto-reconnect attempt {self.reconnect_count} failed: {msg}")
            # Continue trying if we haven't exceeded max retries
            if self.reconnect_count < RECONNECT_MAX_RETRIES:
                # Schedule next attempt (will be called on next read_line)
                pass
            return False
