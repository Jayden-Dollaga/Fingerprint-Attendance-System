import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "python"
sys.path.insert(0, str(PYTHON_ROOT))

from core.utils import format_attendance_display


def test_format_attendance_display_uses_student_name_when_present():
    record = {
        "fingerprint_id": 3,
        "student_name": "Alice",
        "student_no": "S003",
        "grade": "10",
        "section": "A",
        "date": "2026-07-05",
        "time": "13:16:14",
        "confidence": 102,
        "status": "Present",
    }

    display = format_attendance_display(record)

    assert display["student_name"] == "Alice"
    assert display["student_no"] == "S003"
    assert display["status"] == "Present"
    assert display["confidence"] == 102


def test_format_attendance_display_falls_back_to_id_when_name_missing():
    record = {"fingerprint_id": 7, "student_name": None, "status": "Present"}

    display = format_attendance_display(record)

    assert display["student_name"] == "ID:7"
    assert display["status"] == "Present"
