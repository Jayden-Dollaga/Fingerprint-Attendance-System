import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "python"
sys.path.insert(0, str(PYTHON_ROOT))

import core.database as database


def test_clear_all_data_clears_students_and_attendance(tmp_path, monkeypatch):
    db_path = tmp_path / "test_attendance.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_path))

    database.init_database()
    success, _ = database.add_student(1, "S001", "Alice", "10", "A")
    assert success is True

    database.log_attendance(1, 95, "Present")
    database.log_attendance(1, 90, "Present")

    student_count, attendance_count = database.clear_all_data()

    assert student_count == 1
    assert attendance_count == 2
    assert database.get_all_students() == []
    assert database.get_attendance_all() == []
