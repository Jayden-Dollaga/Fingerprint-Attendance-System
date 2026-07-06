import sys
import tkinter as tk
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from gui.app import FingerprintApp


class GuiShutdownTest(unittest.TestCase):
    def test_quit_app_marks_shutdown_and_closes_window(self):
        app = FingerprintApp()
        try:
            app.quit_app()
            self.assertTrue(app._closing)
            with self.assertRaises(tk.TclError):
                app.winfo_exists()
        finally:
            try:
                if app.winfo_exists():
                    app.destroy()
            except tk.TclError:
                pass

    def test_append_log_message_after_destroy_is_safe(self):
        app = FingerprintApp()
        try:
            app.quit_app()
            app._append_log_message("late log update")
        finally:
            try:
                if app.winfo_exists():
                    app.destroy()
            except tk.TclError:
                pass


if __name__ == "__main__":
    unittest.main()
