###############################################################################
#  attendance.py
#  AS608 Fingerprint Attendance System
#
#  Scan processing and duplicate protection logic.
#  Sits between serial_handler (reads raw data) and database (logs it).
###############################################################################

from datetime import datetime

from config import COOLDOWN_SECONDS, MIN_CONFIDENCE
from core.database import log_attendance
from core.logger import log


class AttendanceProcessor:
    def __init__(self):
        self.last_scan  = {}   # {fingerprint_id: datetime of last scan}
        self.current_id = None # Holds ID waiting for CONFIDENCE line

    def process_line(self, line):
        """
        Process one line from ESP32 serial output.
        Returns a result dict if a scan was processed, None otherwise.

        Result dict keys:
            fingerprint_id  int
            confidence      int
            status          str  "GOOD MATCH" or "WEAK MATCH"
            timestamp       datetime
            logged          bool  False if skipped (duplicate/low confidence)
            reason          str  reason if not logged
        """
        if line.startswith("ID:"):
            try:
                self.current_id = int(line.split(":")[1])
            except ValueError:
                self.current_id = None
            return None

        if line == "UNKNOWN":
            # Persist an "unknown" scan so it appears in attendance logs/UI
            # Use fingerprint_id=0 as a sentinel for unregistered/unknown
            now = datetime.now()
            fingerprint_id = 0

            # Rate-limit UNKNOWN scans using the same cooldown mechanism
            if fingerprint_id in self.last_scan:
                elapsed = (now - self.last_scan[fingerprint_id]).total_seconds()
                from config import COOLDOWN_SECONDS
                if elapsed < COOLDOWN_SECONDS:
                    return {
                        "fingerprint_id": fingerprint_id,
                        "confidence": 0,
                        "status": "UNKNOWN",
                        "timestamp": now,
                        "logged": False,
                        "reason": f"Cooldown ({elapsed:.1f}s / {COOLDOWN_SECONDS}s)",
                    }

            try:
                log_attendance(fingerprint_id, 0, "UNKNOWN", now)
                # mark last scan time to enforce future cooldowns
                self.last_scan[fingerprint_id] = now
                return {
                    "fingerprint_id": fingerprint_id,
                    "confidence": 0,
                    "status": "UNKNOWN",
                    "timestamp": now,
                    "logged": True,
                    "reason": None,
                }
            except Exception:
                self.current_id = None
                return None

        if line.startswith("LOW_CONFIDENCE:"):
            self.current_id = None
            return None

        if line.startswith("CONFIDENCE:") and self.current_id is not None:
            try:
                confidence = int(line.split(":")[1])
            except ValueError:
                self.current_id = None
                return None

            fingerprint_id  = self.current_id
            self.current_id = None
            now             = datetime.now()

            # ── Duplicate check ───────────────────────────────────
            if fingerprint_id in self.last_scan:
                elapsed = (now - self.last_scan[fingerprint_id]).total_seconds()
                if elapsed < COOLDOWN_SECONDS:
                    return {
                        "fingerprint_id": fingerprint_id,
                        "confidence":     confidence,
                        "status":         None,
                        "timestamp":      now,
                        "logged":         False,
                        "reason":         f"Cooldown ({elapsed:.1f}s / {COOLDOWN_SECONDS}s)",
                    }

            # ── Determine status ──────────────────────────────────
            status = "GOOD MATCH" if confidence >= MIN_CONFIDENCE else "WEAK MATCH"

            # ── Log to database ───────────────────────────────────
            log_attendance(fingerprint_id, confidence, status, now)
            self.last_scan[fingerprint_id] = now

            return {
                "fingerprint_id": fingerprint_id,
                "confidence":     confidence,
                "status":         status,
                "timestamp":      now,
                "logged":         True,
                "reason":         None,
            }

        return None

    def reset(self):
        """Clear state — call this when switching modes."""
        self.current_id = None
        self.last_scan  = {}
