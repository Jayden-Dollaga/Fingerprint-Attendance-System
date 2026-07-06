###############################################################################
#  core/commands.py
#  AS608 Fingerprint Attendance System
#
#  High-level ESP32 command wrappers.
#  GUI and main.py call these instead of raw serial strings.
###############################################################################

from core.logger import log


def cmd_scan(handler):
    """Tell ESP32 to start attendance scan mode."""
    return handler.send_command("SCAN")

def cmd_stop(handler):
    """Tell ESP32 to stop scanning, return to command mode."""
    return handler.send_command("STOP")

def build_enroll_command(fingerprint_id=None):
    """Build the ESP32 enrollment command for a specific ID or auto-selection."""
    if fingerprint_id is None:
        return "ENROLL"
    if fingerprint_id < 1 or fingerprint_id > 127:
        raise ValueError("fingerprint_id must be between 1 and 127")
    return f"ENROLL:{fingerprint_id}"


def cmd_enroll(handler, fingerprint_id=None):
    """Tell ESP32 to enroll a new finger, using the next free ID when no ID is supplied."""
    if fingerprint_id is not None and (fingerprint_id < 1 or fingerprint_id > 127):
        return False
    return handler.send_command(build_enroll_command(fingerprint_id))

def cmd_delete(handler, fingerprint_id):
    """Tell ESP32 to delete a stored finger by ID."""
    if fingerprint_id < 1 or fingerprint_id > 127:
        return False
    return handler.send_command(f"DELETE:{fingerprint_id}")

def cmd_wipe(handler):
    """Tell ESP32 to wipe ALL stored fingerprints."""
    return handler.send_command("WIPE")

def cmd_list(handler):
    """Ask ESP32 how many fingerprints are stored."""
    return handler.send_command("LIST")
