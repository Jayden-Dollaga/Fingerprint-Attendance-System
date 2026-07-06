import customtkinter as ctk

from config import BAUD_RATE, BAUD_RATES, COM_PORT, get_default_com_port
from settings_store import load_settings


def build_sidebar(app):
    sidebar = ctk.CTkFrame(app, width=280, corner_radius=0)
    sidebar.grid(row=0, column=0, sticky="nsw")
    sidebar.grid_propagate(False)
    sidebar.grid_columnconfigure(0, weight=1)

    # --- App header ---
    header = ctk.CTkFrame(sidebar, fg_color="transparent")
    header.grid(row=0, column=0, padx=16, pady=(20, 10), sticky="ew")
    ctk.CTkLabel(header, text="🖐️  Fingerprint", font=("Segoe UI", 16, "bold")).pack(anchor="w")
    ctk.CTkLabel(header, text="Attendance System", font=("Segoe UI", 12), text_color="#8b8c8d").pack(anchor="w")

    # --- Connection card ---
    connection_card = ctk.CTkFrame(sidebar, corner_radius=10)
    connection_card.grid(row=1, column=0, padx=16, pady=(10, 12), sticky="ew")
    connection_card.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(connection_card, text="ESP32 Connection", font=("Segoe UI", 13, "bold")).grid(
        row=0, column=0, padx=12, pady=(12, 8), sticky="w"
    )

    saved_settings = load_settings()
    initial_port = saved_settings.get("com_port") or get_default_com_port(COM_PORT)
    app.port_var = ctk.StringVar(value=initial_port)
    app.baud_var = ctk.StringVar(value=str(saved_settings.get("baud_rate", BAUD_RATE)))

    port_row = ctk.CTkFrame(connection_card, fg_color="transparent")
    port_row.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")
    port_row.grid_columnconfigure(0, weight=1)

    app.port_combobox = ctk.CTkComboBox(
        port_row,
        values=app.serial_handler.list_available_ports() or [initial_port],
        variable=app.port_var,
        state="normal"
    )
    app.port_combobox.grid(row=0, column=0, sticky="ew")

    ctk.CTkButton(port_row, text="Refresh", width=90, command=app.refresh_serial_ports).grid(
        row=0, column=1, padx=(8, 0)
    )

    ctk.CTkLabel(connection_card, text="Baud Rate", font=("Segoe UI", 11), text_color="#8b8c8d").grid(
        row=2, column=0, padx=12, pady=(0, 0), sticky="w"
    )
    app.baud_combobox = ctk.CTkComboBox(
        connection_card,
        values=[str(rate) for rate in BAUD_RATES],
        variable=app.baud_var,
        state="readonly"
    )
    app.baud_combobox.grid(row=3, column=0, padx=12, pady=(0, 8), sticky="ew")

    app.connect_button = ctk.CTkButton(
        connection_card, text="Connect", command=app.toggle_connection, fg_color="#3b82f6"
    )
    app.connect_button.grid(row=4, column=0, padx=12, pady=(0, 8), sticky="ew")

    status_row = ctk.CTkFrame(connection_card, fg_color="transparent")
    status_row.grid(row=5, column=0, padx=12, pady=(0, 12), sticky="ew")
    app.status_dot = ctk.CTkLabel(status_row, text="●", text_color="#e74c3c", font=("Segoe UI", 14))
    app.status_dot.pack(side="left")
    app.status_var = ctk.StringVar(value="Disconnected")
    ctk.CTkLabel(status_row, textvariable=app.status_var, text_color="#8b8c8d").pack(side="left", padx=(6, 0))

    # --- Quick actions card ---
    actions_card = ctk.CTkFrame(sidebar, corner_radius=10)
    actions_card.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="ew")
    actions_card.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(actions_card, text="Quick Actions", font=("Segoe UI", 13, "bold")).grid(
        row=0, column=0, padx=12, pady=(12, 8), sticky="w"
    )

    app.scan_button = ctk.CTkButton(
        actions_card, text="▶  Start Scan", command=app.start_scan, state="disabled"
    )
    app.scan_button.grid(row=1, column=0, padx=12, pady=4, sticky="ew")

    app.stop_button = ctk.CTkButton(
        actions_card, text="⏹  Stop Scan", command=app.stop_scan, state="disabled",
        fg_color="transparent", border_width=1
    )
    app.stop_button.grid(row=2, column=0, padx=12, pady=4, sticky="ew")

    app.enroll_button = ctk.CTkButton(actions_card, text="➕ Enroll", command=app.enroll_sample)
    app.enroll_button.grid(row=3, column=0, padx=12, pady=(10, 4), sticky="ew")

    app.list_button = ctk.CTkButton(
        actions_card, text="📋 List", command=app.list_fingerprints,
        fg_color="transparent", border_width=1
    )
    app.list_button.grid(row=4, column=0, padx=12, pady=4, sticky="ew")

    app.wipe_button = ctk.CTkButton(
        actions_card, text="⚠ Wipe", command=app.open_wipe_dialog,
        fg_color="#e74c3c", hover_color="#c0392b"
    )
    app.wipe_button.grid(row=5, column=0, padx=12, pady=4, sticky="ew")

    app.backup_button = ctk.CTkButton(
        actions_card, text="💾 Backup DB", command=app.backup_database,
        fg_color="#16a34a", hover_color="#15803d"
    )
    app.backup_button.grid(row=6, column=0, padx=12, pady=4, sticky="ew")

    app.restore_button = ctk.CTkButton(
        actions_card, text="🔁 Restore DB", command=app.open_restore_dialog,
        fg_color="#f59e0b", hover_color="#d97706"
    )
    app.restore_button.grid(row=7, column=0, padx=12, pady=4, sticky="ew")

    app.settings_button = ctk.CTkButton(
        actions_card, text="⚙ Settings", command=app.open_settings_dialog,
        fg_color="#6366f1", hover_color="#4f46e5"
    )
    app.settings_button.grid(row=8, column=0, padx=12, pady=4, sticky="ew")

    app.quit_button = ctk.CTkButton(
        actions_card, text="Quit", command=app.quit_app,
        fg_color="transparent", border_width=1, text_color=("gray10", "gray90")
    )
    app.quit_button.grid(row=9, column=0, padx=12, pady=(10, 12), sticky="ew")

    app.update_button_permissions()

    sidebar.grid_rowconfigure(3, weight=1)

    ctk.CTkLabel(
        sidebar, text="v2.0  ·  ESP32 + Fingerprint Sensor",
        font=("Segoe UI", 10), text_color="#8b8c8d"
    ).grid(row=4, column=0, padx=16, pady=(0, 16), sticky="sw")
