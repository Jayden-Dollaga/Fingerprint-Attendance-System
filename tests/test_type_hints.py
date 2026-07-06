import sys
from pathlib import Path
from typing import get_type_hints

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from core.database import add_student, get_student, get_all_students
from core.serial_handler import SerialHandler, list_serial_ports


def test_core_database_and_serial_helpers_have_type_hints():
    add_student_hints = get_type_hints(add_student)
    get_student_hints = get_type_hints(get_student)
    get_all_students_hints = get_type_hints(get_all_students)
    serial_handler_hints = get_type_hints(SerialHandler.connect)
    list_ports_hints = get_type_hints(list_serial_ports)

    assert "fingerprint_id" in add_student_hints
    assert add_student_hints["fingerprint_id"] is int
    assert get_student_hints["fingerprint_id"] is int
    assert get_all_students_hints.get("return") is not None
    assert serial_handler_hints["port"] is str
    assert list_ports_hints.get("return") is not None
