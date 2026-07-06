import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from gui import app as gui_app


class AttendanceParsingTest(unittest.TestCase):
    def test_registered_scan_is_logged_without_shadowing_error(self):
        app = gui_app.FingerprintApp.__new__(gui_app.FingerprintApp)
        app.last_fingerprint_id = None
        app.last_confidence = 0
        app.last_logged_time = 0.0
        app.last_logged_id = None
        app.attendance_mode = "Today"
        app.attendance_offset = 0
        app.after = lambda *args, **kwargs: None
        app.log_message = lambda message: None
        app._build_attendance_card = lambda *args, **kwargs: None

        with patch.object(gui_app, "get_student", return_value={"student_name": "Alice", "student_no": "2026-001", "grade": "10", "section": "A"}), \
             patch.object(gui_app, "log_attendance") as mock_log_attendance:
            app._parse_attendance("ID:1")
            app._parse_attendance("CONFIDENCE:258")

        self.assertEqual(mock_log_attendance.call_count, 1)
        self.assertEqual(mock_log_attendance.call_args.kwargs["fingerprint_id"], 1)
        self.assertEqual(mock_log_attendance.call_args.kwargs["confidence"], 258)
        self.assertEqual(mock_log_attendance.call_args.kwargs["status"], "Present")


if __name__ == "__main__":
    unittest.main()
