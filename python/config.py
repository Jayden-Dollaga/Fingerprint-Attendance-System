###############################################################################
#  config.py
#  AS608 Fingerprint Attendance System
#
#  All configuration lives here.
#  Change settings here instead of hunting through multiple files.
###############################################################################

from pathlib import Path

try:
    from serial.tools import list_ports
except Exception:  # pragma: no cover - optional dependency on non-serial setups
    list_ports = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def discover_serial_ports():
    """Return a list of available serial ports, if pyserial is available."""
    if list_ports is None:
        return []
    try:
        return [port.device for port in list_ports.comports()]
    except Exception:
        return []


def get_default_com_port(default_fallback: str = "COM5") -> str:
    """Choose the most likely ESP32 serial port and fall back to the configured default."""
    if list_ports is None:
        return default_fallback

    try:
        ports = list_ports.comports()
    except Exception:
        return default_fallback

    if not ports:
        return default_fallback

    keywords = [
        "cp210",
        "ch340",
        "usb serial",
        "silicon labs",
        "uart",
        "esp32",
        "arduino",
    ]
    known_vid_pids = {
        "10c4:ea60": 140,  # CP2102
        "1a86:7523": 140,  # CH340
        "0403:6001": 120,  # FT232
        "1a86:55d3": 120,  # CH340 alternative
    }
    scored_ports = []
    for port in ports:
        device = (getattr(port, "device", "") or "").lower()
        description = (getattr(port, "description", "") or "").lower()
        combined = f"{device} {description}"
        vid = getattr(port, "vid", None)
        pid = getattr(port, "pid", None)
        vid_pid = f"{vid:x}:{pid:x}" if vid is not None and pid is not None else ""
        score = 0
        if vid_pid in known_vid_pids:
            score += known_vid_pids[vid_pid]
        if any(keyword in combined for keyword in keywords):
            score += 80
        if "bluetooth" in combined or "bt" in combined:
            score -= 100
        if "com" in device:
            score += 10
        if "usb" in combined:
            score += 10
        scored_ports.append((score, device, getattr(port, "description", "")))

    scored_ports.sort(key=lambda item: item[0], reverse=True)
    best_port = None
    for score, device, description in scored_ports:
        if device:
            best_port = device
            if score >= 80:
                return best_port
    return best_port or default_fallback


# ── Serial / ESP32 ────────────────────────────────────────────────────────────
COM_PORT         = get_default_com_port()  # Auto-detect first available serial port when possible
BAUD_RATE        = 115200     # Must match Serial.begin() in Arduino sketch
BAUD_RATES       = [9600, 19200, 38400, 57600, 115200]
AUTO_SCAN        = True       # Auto-send SCAN command when Python connects

# ── GUI / behavior defaults ──────────────────────────────────────────────────────
THEME_MODES      = ["Dark", "Light"]

# ── Attendance ────────────────────────────────────────────────────────────────
COOLDOWN_SECONDS = 10         # Ignore same finger within this many seconds
MIN_CONFIDENCE   = 100        # Below this = WEAK MATCH, above = GOOD MATCH

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH          = str(DATA_DIR / "attendance.db")

# ── Export ────────────────────────────────────────────────────────────────────
EXPORT_FOLDER    = str(DATA_DIR / "exports")  # Folder where Excel exports are saved

# ── Boot noise from ESP32 to silently ignore ──────────────────────────────────
IGNORE_PREFIXES = [
    "rst:", "load:", "entry", "configsip", "mode:", "ho ",
    "clk_", "========", "Commands", "ENROLL:", "DELETE:",
    "WIPE", "LIST", "SCAN", "STOP", "Place finger",
    "Enroll finger", "Delete finger", "Delete ALL",
    "Show stored", "Start attendance", "Stop scanning",
    "line ending",
]
# ── Logging ───────────────────────────────────────────────────────────────────
LOG_TO_FILE           = True                # Set to True to enable file logging
LOG_FOLDER            = str(DATA_DIR / "logs")  # Where logs are saved
ENABLE_DEBUG_LOGGING  = False               # Set to True for verbose debug output

# ── Auto-Reconnect ────────────────────────────────────────────────────────────
AUTO_RECONNECT        = True                # Enable automatic reconnection on disconnect
RECONNECT_MAX_RETRIES = 5                   # Maximum number of reconnection attempts
RECONNECT_BASE_DELAY  = 2                   # Base delay in seconds (exponential backoff)

# ── User Roles ────────────────────────────────────────────────────────────────
USER_ROLES = {
    "admin": {
        "name": "Administrator",
        "permissions": ["scan", "enroll", "delete", "wipe", "export", "backup", "restore"],
        "can_manage_users": True,
    },
    "teacher": {
        "name": "Teacher",
        "permissions": ["scan", "export", "backup"],
        "can_manage_users": False,
    },
    "guest": {
        "name": "Guest",
        "permissions": ["scan"],
        "can_manage_users": False,
    },
}

DEFAULT_USER_ROLE = "admin"  # Change to 'teacher' or 'guest' to restrict permissions  # Default role for new users