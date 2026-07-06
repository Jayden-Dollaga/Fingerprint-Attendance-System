###############################################################################
#  config.py
#  AS608 Fingerprint Attendance System
#
#  All configuration lives here.
#  Change settings here instead of hunting through multiple files.
###############################################################################

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# ── Serial / ESP32 ────────────────────────────────────────────────────────────
COM_PORT         = "COM5"     # Change to match your ESP32 port
BAUD_RATE        = 115200     # Must match Serial.begin() in Arduino sketch
AUTO_SCAN        = True       # Auto-send SCAN command when Python connects

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