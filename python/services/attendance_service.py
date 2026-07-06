from core.database import get_attendance_paginated, get_attendance_today, log_attendance


class AttendanceService:
    """Thin service layer for attendance data operations."""

    def get_today(self):
        return get_attendance_today()

    def get_paginated(self, limit, offset):
        return get_attendance_paginated(limit=limit, offset=offset)

    def log(self, fingerprint_id, confidence, status):
        return log_attendance(fingerprint_id=fingerprint_id, confidence=confidence, status=status)
