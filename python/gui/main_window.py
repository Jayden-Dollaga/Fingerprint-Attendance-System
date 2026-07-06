import tkinter as tk
from tkinter import ttk


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fingerprint Attendance System")
        self.geometry("900x600")
        self.minsize(800, 500)

        self._build_ui()

    def _build_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.attendance_tab = ttk.Frame(self.notebook)
        self.students_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.attendance_tab, text="Attendance")
        self.notebook.add(self.students_tab, text="Students")
        self.notebook.add(self.settings_tab, text="Settings")

        ttk.Label(self.attendance_tab, text="Live attendance view").pack(padx=20, pady=20)
        ttk.Label(self.students_tab, text="Student management view").pack(padx=20, pady=20)
        ttk.Label(self.settings_tab, text="Connection and export settings").pack(padx=20, pady=20)


def run_gui():
    app = MainWindow()
    app.mainloop()
