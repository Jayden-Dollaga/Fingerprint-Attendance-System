import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = PROJECT_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


class ProjectStructureTests(unittest.TestCase):
    def test_core_modules_import(self):
        import main
        import core.database as database
        import core.serial_handler as serial_handler
        import core.attendance as attendance

        self.assertTrue(hasattr(main, "main"))
        self.assertTrue(callable(database.init_database))
        self.assertTrue(hasattr(serial_handler, "SerialHandler"))
        self.assertTrue(hasattr(attendance, "AttendanceProcessor"))


if __name__ == "__main__":
    unittest.main()
