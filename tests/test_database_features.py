import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from core import database


class DatabaseFeaturesTest(unittest.TestCase):
    def test_clear_all_students_removes_all_profiles(self):
        database.init_database()
        database.register_student(999999, "TEST-001", "Test User", "12", "A")

        cleared = database.clear_all_students()

        self.assertGreaterEqual(cleared, 1)
        self.assertEqual(database.get_student_count(), 0)
        self.assertIsNone(database.get_student(999999))


if __name__ == "__main__":
    unittest.main()
