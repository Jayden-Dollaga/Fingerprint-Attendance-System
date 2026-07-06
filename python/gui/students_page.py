from tkinter import ttk


class StudentsPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="Students page placeholder").pack(padx=20, pady=20)
