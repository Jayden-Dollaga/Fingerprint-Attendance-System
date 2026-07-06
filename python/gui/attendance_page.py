from tkinter import ttk


class AttendancePage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="Attendance page placeholder").pack(padx=20, pady=20)
