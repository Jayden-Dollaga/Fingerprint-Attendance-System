import customtkinter as ctk
from tkinter import messagebox

class SettingsPage:
    """Settings page scaffold for application preferences."""

    def __init__(self, app):
        self.app = app
        self.container = None

    def build(self, parent):
        self.container = ctk.CTkFrame(parent, fg_color="transparent")
        self.container.grid(sticky="nsew")
        ctk.CTkLabel(self.container, text="Settings", font=("Segoe UI", 14, "bold")).pack(padx=12, pady=12)

        # Example setting: COM port default
        ctk.CTkLabel(self.container, text="Default COM Port:").pack(anchor="w", padx=12)
        self.com_var = ctk.StringVar(value=getattr(self.app, 'port_var', ctk.StringVar(value='')))
        self.com_entry = ctk.CTkEntry(self.container, textvariable=self.com_var)
        self.com_entry.pack(fill='x', padx=12, pady=(0,12))

        save_btn = ctk.CTkButton(self.container, text="Save Settings", command=self.save)
        save_btn.pack(padx=12, pady=(6,12))
        return self.container

    def save(self):
        # Persist settings to config or inform the app
        # For now, just show a confirmation
        messagebox.showinfo("Settings", "Settings saved (not yet persisted).")

    def refresh(self):
        # Refresh UI fields from app state if needed
        if self.container is None:
            return
        try:
            self.com_var.set(getattr(self.app, 'port_var', ''))
        except Exception:
            pass
