import customtkinter as ctk
from tkinter import messagebox

from config import BAUD_RATES, THEME_MODES
from settings_store import save_settings


def open_settings_dialog(app):
    """Open the runtime settings dialog for the main GUI."""
    if hasattr(app, "settings_dialog") and app.settings_dialog is not None and app.settings_dialog.winfo_exists():
        app.settings_dialog.lift()
        app.settings_dialog.focus()
        return

    dialog = ctk.CTkToplevel(app)
    dialog.title("Application Settings")
    dialog.geometry("420x420")
    dialog.transient(app)
    dialog.grab_set()
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_rowconfigure(0, weight=1)

    content = ctk.CTkFrame(dialog, corner_radius=10)
    content.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
    content.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(content, text="Settings", font=("Segoe UI", 16, "bold")).grid(
        row=0, column=0, sticky="w", pady=(0, 12)
    )

    ctk.CTkLabel(content, text="COM Port", font=("Segoe UI", 11)).grid(
        row=1, column=0, sticky="w", pady=(4, 2)
    )
    port_menu = ctk.CTkComboBox(
        content,
        values=app.serial_handler.list_available_ports() or [app.port_var.get()],
        variable=app.port_var,
        state="normal"
    )
    port_menu.grid(row=2, column=0, sticky="ew", pady=(0, 8))

    refresh_ports_button = ctk.CTkButton(
        content,
        text="Refresh Ports",
        width=120,
        command=lambda: _refresh_ports(port_menu, app)
    )
    refresh_ports_button.grid(row=3, column=0, sticky="w", pady=(0, 12))

    ctk.CTkLabel(content, text="Baud Rate", font=("Segoe UI", 11)).grid(
        row=4, column=0, sticky="w", pady=(4, 2)
    )
    baud_menu = ctk.CTkComboBox(
        content,
        values=[str(rate) for rate in BAUD_RATES],
        variable=app.baud_var,
        state="readonly"
    )
    baud_menu.grid(row=5, column=0, sticky="ew", pady=(0, 8))

    ctk.CTkLabel(content, text="Theme Mode", font=("Segoe UI", 11)).grid(
        row=6, column=0, sticky="w", pady=(4, 2)
    )
    theme_var = ctk.StringVar(value=app.settings.get("theme", "dark"))
    theme_menu = ctk.CTkOptionMenu(
        content,
        values=THEME_MODES,
        variable=theme_var,
        command=lambda value: ctk.set_appearance_mode(value)
    )
    theme_menu.grid(row=7, column=0, sticky="ew", pady=(0, 8))

    auto_reconnect_var = ctk.BooleanVar(value=app.serial_handler.auto_reconnect_enabled)
    ctk.CTkCheckBox(
        content,
        text="Enable Auto-Reconnect",
        variable=auto_reconnect_var
    ).grid(row=8, column=0, sticky="w", pady=(4, 12))

    button_row = ctk.CTkFrame(content, fg_color="transparent")
    button_row.grid(row=9, column=0, sticky="ew", pady=(12, 0))
    button_row.grid_columnconfigure((0, 1), weight=1)

    def _save_settings():
        try:
            app.serial_handler.auto_reconnect_enabled = auto_reconnect_var.get()
            if theme_var.get():
                ctk.set_appearance_mode("Dark" if theme_var.get().lower() == "dark" else "Light")
            app.settings = {
                "com_port": app.port_var.get().strip() if getattr(app, "port_var", None) else "",
                "baud_rate": int(app.baud_var.get()) if getattr(app, "baud_var", None) else 115200,
                "cooldown": app.settings.get("cooldown", 10),
                "theme": theme_var.get().lower(),
                "auto_reconnect": auto_reconnect_var.get(),
            }
            save_settings(app.settings)
            app.log_message("Settings updated.")
            dialog.destroy()
        except Exception as err:
            messagebox.showerror("Settings Error", f"Could not save settings: {err}", parent=dialog)

    ctk.CTkButton(
        button_row,
        text="Save",
        command=_save_settings,
        height=40,
        corner_radius=8,
    ).grid(row=0, column=0, padx=(0, 8), sticky="ew")
    ctk.CTkButton(
        button_row,
        text="Close",
        fg_color="transparent",
        border_width=1,
        command=dialog.destroy,
        height=40,
        corner_radius=8,
    ).grid(row=0, column=1, sticky="ew")

    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    app.settings_dialog = dialog


def _refresh_ports(port_menu, app):
    ports = app.serial_handler.list_available_ports() or []
    if ports:
        port_menu.configure(values=ports)
        app.port_var.set(ports[0])
    else:
        port_menu.configure(values=[app.port_var.get()])
    app.log_message("Serial port list refreshed.")
