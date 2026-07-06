from tkinter import ttk


class SettingsPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="Settings page placeholder").pack(padx=20, pady=20)
