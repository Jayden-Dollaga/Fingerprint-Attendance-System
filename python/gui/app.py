import sys
import threading
import time
import re
from pathlib import Path
from datetime import datetime
from tkinter import messagebox, filedialog

PYTHON_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

import customtkinter as ctk

from config import COM_PORT, RECONNECT_MAX_RETRIES
from core.serial_handler import SerialHandler
from core.commands import cmd_scan, cmd_stop, cmd_enroll, cmd_delete, cmd_wipe, cmd_list
from core.database import (
    init_database,
    get_attendance_all,
    get_attendance_today,
    register_student,
    get_all_students,
    get_student,
    delete_student,
    clear_all_students,
    clear_all_data,
    generate_statistics_report,
    generate_attendance_chart,
    generate_section_chart,
    generate_grade_chart,
    backup_database as backup_database_service,
    restore_database,
    list_backups,
    log_attendance,
    get_attendance_paginated,
)
from core.utils import format_attendance_display

# Image handling for charts
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# ---- Palette -----------------------------------------------------------
COLOR_CONNECTED = "#2ecc71"
COLOR_DISCONNECTED = "#e74c3c"
COLOR_MUTED = "#8b8b8b"
COLOR_ACCENT = "#3b82f6"
COLOR_DANGER = "#e74c3c"
COLOR_DANGER_HOVER = "#c0392b"
MONO_FONT = ("Consolas", 12)
HEADER_FONT = ("Segoe UI", 16, "bold")
SUBHEADER_FONT = ("Segoe UI", 13, "bold")

# ESP32 output patterns that drive the enroll popup
RE_ENROLLING_AS = re.compile(r"ENROLLING FINGER AS ID #(\d+)", re.IGNORECASE)
RE_ENROLL_SUCCESS = re.compile(r"SUCCESS!?\s*Finger saved as ID #(\d+)", re.IGNORECASE)
RE_ENROLL_CANCEL = re.compile(r"ENROLLMENT cancelled|Enrollment cancelled|ENROLL_CANCELLED", re.IGNORECASE)

# ESP32 output patterns that drive the wipe popup
RE_WIPE_START = re.compile(r"Wiping ALL fingerprints", re.IGNORECASE)
RE_WIPE_SUCCESS = re.compile(r"SUCCESS\s*-\s*All fingerprints deleted", re.IGNORECASE)

# ESP32 output patterns for attendance logging
RE_ID_FOUND = re.compile(r"^ID[:\s]+(\d+)\s*$", re.IGNORECASE)
RE_CONFIDENCE = re.compile(r"^CONFIDENCE[:\s]+(\d+)\s*$", re.IGNORECASE)
RE_UNKNOWN = re.compile(r"^UNKNOWN\s*$", re.IGNORECASE)


class FingerprintApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Fingerprint Attendance System")
        self.geometry("1120x700")
        self.minsize(960, 600)

        self.serial_handler = SerialHandler()
        self.stop_event = threading.Event()
        self.reader_thread = None
        self._closing = False
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

        # Enroll popup state
        self.enroll_dialog = None
        self.enroll_log_text = None
        self.enroll_save_button = None
        self.enroll_completed = False
        self.enroll_ready_to_save = False

        # Wipe popup state
        self.wipe_dialog = None
        self.wipe_log_text = None
        self.wipe_status_var = None
        self.wipe_confirm_button = None

        # Student roster popup state (opened from "List")
        self.students_dialog = None
        self.students_list_frame = None

        # Attendance tracking state (for auto-logging)
        self.last_fingerprint_id = None        # Most recently detected fingerprint ID
        self.last_id_time = 0                  # When it was detected
        self.ID_TIMEOUT = 2.0                  # Seconds before an ID expires without confidence
        self.last_confidence = 0               # Its confidence value
        self.last_logged_times = {}            # Per-fingerprint cooldown tracking

        # User role system
        from config import DEFAULT_USER_ROLE
        self.current_role = DEFAULT_USER_ROLE

        self.init_database()
        self.build_ui()

    def init_database(self):
        init_database()

    # ------------------------------------------------------------------
    # Role & Permissions
    # ------------------------------------------------------------------
    def has_permission(self, permission: str) -> bool:
        """Check if current user role has a specific permission."""
        from config import USER_ROLES
        role_config = USER_ROLES.get(self.current_role, {})
        return permission in role_config.get("permissions", [])

    def update_button_permissions(self):
        """Update button states based on current user role."""
        self.enroll_button.configure(state="normal" if self.has_permission("enroll") else "disabled")
        self.wipe_button.configure(state="normal" if self.has_permission("wipe") else "disabled")
        self.backup_button.configure(state="normal" if self.has_permission("backup") else "disabled")
        self.restore_button.configure(state="normal" if self.has_permission("restore") else "disabled")

    def change_role(self, new_role: str):
        """Switch to a different user role and update permissions."""
        from config import USER_ROLES
        if new_role in USER_ROLES:
            self.current_role = new_role
            self.update_button_permissions()
            role_name = USER_ROLES[new_role].get("name", new_role)
            self.log_message(f"🔐 Switched to {role_name} role")
            if hasattr(self, "role_label"):
                self.role_label.configure(text=f"👤 {role_name}")

    def _on_role_changed(self, choice: str):
        """Handle role dropdown selection."""
        from config import USER_ROLES
        # Find the role key that matches the selected role name
        for role_key, role_config in USER_ROLES.items():
            if role_config.get("name", role_key) == choice:
                self.change_role(role_key)
                break

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def build_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.build_sidebar()
        self.build_main_area()

    def build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)

        # --- App header ---
        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=(20, 10), sticky="ew")
        ctk.CTkLabel(header, text="🖐️  Fingerprint", font=HEADER_FONT).pack(anchor="w")
        ctk.CTkLabel(header, text="Attendance System", font=("Segoe UI", 12), text_color=COLOR_MUTED).pack(anchor="w")

        # --- Connection card ---
        connection_card = ctk.CTkFrame(sidebar, corner_radius=10)
        connection_card.grid(row=1, column=0, padx=16, pady=(10, 12), sticky="ew")
        connection_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(connection_card, text="ESP32 Connection", font=SUBHEADER_FONT).grid(
            row=0, column=0, padx=12, pady=(12, 8), sticky="w"
        )

        self.port_var = ctk.StringVar(value=COM_PORT)
        self.port_entry = ctk.CTkEntry(connection_card, textvariable=self.port_var, placeholder_text="COM port")
        self.port_entry.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")

        self.connect_button = ctk.CTkButton(
            connection_card, text="Connect", command=self.toggle_connection, fg_color=COLOR_ACCENT
        )
        self.connect_button.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="ew")

        status_row = ctk.CTkFrame(connection_card, fg_color="transparent")
        status_row.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="ew")
        self.status_dot = ctk.CTkLabel(status_row, text="●", text_color=COLOR_DISCONNECTED, font=("Segoe UI", 14))
        self.status_dot.pack(side="left")
        self.status_var = ctk.StringVar(value="Disconnected")
        ctk.CTkLabel(status_row, textvariable=self.status_var, text_color=COLOR_MUTED).pack(side="left", padx=(6, 0))

        # --- Quick actions card ---
        actions_card = ctk.CTkFrame(sidebar, corner_radius=10)
        actions_card.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="ew")
        actions_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(actions_card, text="Quick Actions", font=SUBHEADER_FONT).grid(
            row=0, column=0, padx=12, pady=(12, 8), sticky="w"
        )

        self.scan_button = ctk.CTkButton(
            actions_card, text="▶  Start Scan", command=self.start_scan, state="disabled"
        )
        self.scan_button.grid(row=1, column=0, padx=12, pady=4, sticky="ew")

        self.stop_button = ctk.CTkButton(
            actions_card, text="⏹  Stop Scan", command=self.stop_scan, state="disabled",
            fg_color="transparent", border_width=1
        )
        self.stop_button.grid(row=2, column=0, padx=12, pady=4, sticky="ew")

        self.enroll_button = ctk.CTkButton(actions_card, text="➕ Enroll", command=self.enroll_sample)
        self.enroll_button.grid(row=3, column=0, padx=12, pady=(10, 4), sticky="ew")

        self.list_button = ctk.CTkButton(
            actions_card, text="📋 List", command=self.list_fingerprints,
            fg_color="transparent", border_width=1
        )
        self.list_button.grid(row=4, column=0, padx=12, pady=4, sticky="ew")

        self.wipe_button = ctk.CTkButton(
            actions_card, text="⚠ Wipe", command=self.open_wipe_dialog,
            fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER
        )
        self.wipe_button.grid(row=5, column=0, padx=12, pady=4, sticky="ew")

        self.backup_button = ctk.CTkButton(
            actions_card, text="💾 Backup DB", command=self.backup_database,
            fg_color="#16a34a", hover_color="#15803d"
        )
        self.backup_button.grid(row=6, column=0, padx=12, pady=4, sticky="ew")

        self.restore_button = ctk.CTkButton(
            actions_card, text="🔁 Restore DB", command=self.open_restore_dialog,
            fg_color="#f59e0b", hover_color="#d97706"
        )
        self.restore_button.grid(row=7, column=0, padx=12, pady=4, sticky="ew")

        self.quit_button = ctk.CTkButton(
            actions_card, text="Quit", command=self.quit_app,
            fg_color="transparent", border_width=1, text_color=("gray10", "gray90")
        )
        self.quit_button.grid(row=8, column=0, padx=12, pady=(10, 12), sticky="ew")

        # Update button permissions based on user role
        self.update_button_permissions()

        # Empty flexible row so the footer sits at the bottom of the sidebar
        sidebar.grid_rowconfigure(3, weight=1)

        # --- Footer ---
        ctk.CTkLabel(
            sidebar, text="v1.0  ·  ESP32 + Fingerprint Sensor",
            font=("Segoe UI", 10), text_color=COLOR_MUTED
        ).grid(row=4, column=0, padx=16, pady=(0, 16), sticky="sw")

    def build_main_area(self):
        main = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        # --- Header with role selector ---
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        # Role selector on the right
        role_frame = ctk.CTkFrame(header, fg_color="transparent")
        role_frame.grid(row=0, column=1, sticky="e")

        from config import USER_ROLES
        role_names = list(USER_ROLES.keys())
        role_labels = [USER_ROLES[role].get("name", role) for role in role_names]

        self.role_label = ctk.CTkLabel(
            role_frame, text=f"👤 {USER_ROLES[self.current_role].get('name', self.current_role)}",
            font=("Segoe UI", 11), text_color=COLOR_ACCENT
        )
        self.role_label.grid(row=0, column=0, padx=(0, 8), sticky="e")

        self.role_dropdown = ctk.CTkComboBox(
            role_frame, values=role_labels, state="readonly",
            width=120, command=self._on_role_changed
        )
        self.role_dropdown.set(USER_ROLES[self.current_role].get("name", self.current_role))
        self.role_dropdown.grid(row=0, column=1, sticky="e")

        # Tabview below
        self.tabview = ctk.CTkTabview(main)
        self.tabview.grid(row=1, column=0, sticky="nsew")
        self.tabview.add("📅 Attendance")
        self.tabview.add("📊 Statistics")
        self.tabview.add("🖥 Live Log")

        self.build_attendance_tab(self.tabview.tab("📅 Attendance"))
        self.build_statistics_tab(self.tabview.tab("📊 Statistics"))
        self.build_log_tab(self.tabview.tab("🖥 Live Log"))

    def build_attendance_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        header_row = ctk.CTkFrame(tab, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_row, text="Attendance Records", font=SUBHEADER_FONT).grid(
            row=0, column=0, sticky="w"
        )
        # View mode: Today or Recent
        self.attendance_mode_var = ctk.StringVar(value="Today")
        self.attendance_mode = "Today"
        self.attendance_mode_var.set("Today")
        mode_menu = ctk.CTkOptionMenu(header_row, values=["Today", "Recent"], variable=self.attendance_mode_var,
                                      command=self._on_attendance_mode_changed)
        mode_menu.grid(row=0, column=1, sticky="e", padx=(0, 8))
        self.refresh_button = ctk.CTkButton(header_row, text="↻ Refresh", width=100, command=self.refresh_attendance_view)
        self.refresh_button.grid(row=0, column=2, sticky="e")

        card = ctk.CTkFrame(tab, corner_radius=10)
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)

        self.attendance_scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.attendance_scroll.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        self.attendance_scroll.grid_columnconfigure(0, weight=1)
        # Pagination state
        self.attendance_page_size = 100
        self.attendance_offset = 0
        # Load more button
        self.load_more_button = ctk.CTkButton(card, text="Load more", command=self.load_more_attendance)
        self.load_more_button.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 12))
        self.refresh_attendance_view()
        self._update_load_more_visibility()

    def _on_attendance_mode_changed(self, choice: str):
        self.attendance_mode = choice
        # Reset pagination when switching to Recent
        if choice == "Recent":
            self.attendance_offset = 0
        self.refresh_attendance_view()

    def _update_load_more_visibility(self):
        button = getattr(self, 'load_more_button', None)
        if button is None:
            return
        if getattr(self, 'attendance_mode', 'Today') == 'Recent':
            button.configure(state='normal')
        else:
            button.configure(state='disabled')

    def build_statistics_tab(self, tab):
        """Build the statistics dashboard tab."""
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=0)
        tab.grid_rowconfigure(1, weight=1)

        # Header
        header_row = ctk.CTkFrame(tab, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_row, text="Attendance Statistics Dashboard", font=SUBHEADER_FONT).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkButton(header_row, text="↻ Refresh", width=100, command=self.refresh_statistics).grid(
            row=0, column=1, sticky="e"
        )

        # Stats container
        stats_frame = ctk.CTkFrame(tab, corner_radius=0)
        stats_frame.grid(row=1, column=0, sticky="nsew")
        stats_frame.grid_columnconfigure(0, weight=1)
        stats_frame.grid_rowconfigure(0, weight=1)

        # Create a scrollable frame for stats
        scrollable = ctk.CTkScrollableFrame(stats_frame, fg_color="transparent")
        scrollable.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        scrollable.grid_columnconfigure(0, weight=1)

        # Stats grid (4 columns)
        scrollable.grid_columnconfigure((0, 1), weight=1)

        # Row 1: Key metrics
        metrics_data = [
            ("Total Students", lambda: str(len(get_all_students())), COLOR_ACCENT),
            ("Total Attendance Logs", lambda: str(len(get_attendance_all())), COLOR_ACCENT),
        ]

        col = 0
        for i, (label, value_fn, color) in enumerate(metrics_data):
            card = ctk.CTkFrame(scrollable, corner_radius=10, fg_color="#2a2a2a")
            card.grid(row=0, column=i, padx=8, pady=8, sticky="ew")
            card.grid_columnconfigure(0, weight=1)

            try:
                value = value_fn()
            except:
                value = "—"

            ctk.CTkLabel(card, text=label, font=("Segoe UI", 10), text_color=COLOR_MUTED).pack(
                padx=14, pady=(10, 4)
            )
            ctk.CTkLabel(card, text=value, font=("Segoe UI", 24, "bold"), text_color=COLOR_ACCENT).pack(
                padx=14, pady=(0, 12)
            )

        # Row 2: Stats summary
        summary_card = ctk.CTkFrame(scrollable, corner_radius=10)
        summary_card.grid(row=1, column=0, columnspan=2, padx=8, pady=8, sticky="ew")
        summary_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(summary_card, text="📊 Summary", font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=14, pady=(12, 8)
        )

        # Summary text
        try:
            from core.database import count_attendance_by_date
            
            today_date = str(datetime.now().date())
            today_count = count_attendance_by_date(today_date)
            
            summary_text = (
                f"Today's Attendance: {today_count} students\n"
                f"Total Students: {len(get_all_students())}\n"
                f"Total Records: {len(get_attendance_all())}\n"
                f"\nSystem is {('Connected' if self.serial_handler.connected else 'Disconnected')}"
            )
        except Exception as e:
            summary_text = f"Could not load statistics: {e}"

        ctk.CTkLabel(
            summary_card, text=summary_text, font=("Segoe UI", 11),
            text_color=COLOR_MUTED, justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 12))

        # Report generation section
        report_card = ctk.CTkFrame(scrollable, corner_radius=10)
        report_card.grid(row=2, column=0, columnspan=2, padx=8, pady=8, sticky="ew")
        report_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(report_card, text="📄 Generate Report", font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=14, pady=(12, 8)
        )

        button_row = ctk.CTkFrame(report_card, fg_color="transparent")
        button_row.pack(anchor="w", padx=14, pady=(0, 12), fill="x")

        ctk.CTkButton(
            button_row, text="📋 View Report", width=140, command=self.show_statistics_report,
            state="normal" if self.has_permission("export") else "disabled"
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            button_row, text="💾 Export Report", width=140, command=self.export_statistics_report,
            fg_color="#27ae60",
            state="normal" if self.has_permission("export") else "disabled"
        ).pack(side="left", padx=(0, 8))

        # Charts section
        if PILLOW_AVAILABLE:
            charts_card = ctk.CTkFrame(scrollable, corner_radius=10)
            charts_card.grid(row=3, column=0, columnspan=2, padx=8, pady=8, sticky="ew")
            charts_card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(charts_card, text="📈 Visual Analytics", font=("Segoe UI", 13, "bold")).pack(
                anchor="w", padx=14, pady=(12, 8)
            )

            button_row = ctk.CTkFrame(charts_card, fg_color="transparent")
            button_row.pack(anchor="w", padx=14, pady=(0, 12), fill="x")

            ctk.CTkButton(
                button_row, text="📊 Show Charts", width=140, command=self.show_statistics_charts,
                fg_color="#9333ea"
            ).pack(side="left", padx=(0, 8))

    def refresh_statistics(self):
        """Refresh the statistics display."""
        if not self._ui_ready():
            return

        try:
            statistics_tab = self.tabview.tab("📊 Statistics")
            for child in statistics_tab.winfo_children():
                child.destroy()
            self.build_statistics_tab(statistics_tab)
            self.tabview.set("📊 Statistics")
            self.log_message("Statistics refreshed")
        except Exception as e:
            self.log_message(f"Could not refresh statistics: {e}")

    def show_statistics_report(self):
        """Display the generated statistics report in a popup dialog."""
        if not self.has_permission("export"):
            messagebox.showerror("Permission Denied", "Your role cannot view reports.", parent=self)
            return
        try:
            from core.database import generate_statistics_report
            report = generate_statistics_report()
            
            # Create report dialog
            dialog = ctk.CTkToplevel(self)
            dialog.title("Statistics Report")
            dialog.geometry("800x600")
            
            # Header
            header = ctk.CTkFrame(dialog, fg_color="transparent")
            header.pack(padx=16, pady=(16, 8), fill="x")
            ctk.CTkLabel(header, text="📊 Attendance Statistics Report", font=SUBHEADER_FONT).pack(anchor="w")
            
            # Report text
            text_widget = ctk.CTkTextbox(dialog, font=("Consolas", 10), wrap="none")
            text_widget.pack(padx=12, pady=(0, 12), fill="both", expand=True)
            text_widget.insert("1.0", report)
            text_widget.configure(state="disabled")
            
            # Button row
            button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            button_frame.pack(padx=16, pady=(0, 16), fill="x")
            
            ctk.CTkButton(button_frame, text="Copy to Clipboard", width=150, command=lambda: self._copy_to_clipboard(report)).pack(side="left", padx=(0, 8))
            ctk.CTkButton(button_frame, text="Close", width=150, fg_color="transparent", border_width=1, command=dialog.destroy).pack(side="left")
            
            self.log_message("Statistics report generated")
        except Exception as e:
            messagebox.showerror("Report Error", f"Could not generate report: {e}")

    def export_statistics_report(self):
        """Export the statistics report to a text file."""
        if not self.has_permission("export"):
            messagebox.showerror("Permission Denied", "Your role cannot export reports.", parent=self)
            return
        try:
            from core.database import generate_statistics_report
            from tkinter import filedialog
            
            report = generate_statistics_report()
            
            # Ask for file location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
                initialfile=f"attendance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            
            if not file_path:
                return
            
            # Write file
            with open(file_path, 'w') as f:
                f.write(report)
            
            self.log_message(f"Report exported to {file_path}")
            messagebox.showinfo("Export Successful", f"Report saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not export report: {e}")

    def _copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
            self.log_message("Report copied to clipboard")
        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Could not copy: {e}")

    def show_statistics_charts(self):
        """Display generated charts in a popup dialog."""
        try:
            if not PILLOW_AVAILABLE:
                messagebox.showwarning("Charts Not Available", "Pillow library not installed. Install with: pip install pillow")
                return
            
            # Generate charts
            attendance_chart = generate_attendance_chart()
            section_chart = generate_section_chart()
            grade_chart = generate_grade_chart()
            
            if not any([attendance_chart, section_chart, grade_chart]):
                messagebox.showwarning("No Data", "Insufficient data to generate charts. Ensure there are attendance records.")
                return
            
            # Create dialog
            dialog = ctk.CTkToplevel(self)
            dialog.title("Statistics Charts")
            dialog.geometry("1000x700")
            
            # Header
            header = ctk.CTkFrame(dialog, fg_color="transparent")
            header.pack(padx=16, pady=(16, 8), fill="x")
            ctk.CTkLabel(header, text="📈 Attendance Analytics Charts", font=SUBHEADER_FONT).pack(anchor="w")
            
            # Tabs for charts
            tabview = ctk.CTkTabview(dialog)
            tabview.pack(padx=12, pady=12, fill="both", expand=True)
            
            # Chart tabs
            if attendance_chart:
                tabview.add("📅 Timeline")
                self._display_chart_in_tab(tabview.tab("📅 Timeline"), attendance_chart)
            
            if section_chart:
                tabview.add("📊 By Section")
                self._display_chart_in_tab(tabview.tab("📊 By Section"), section_chart)
            
            if grade_chart:
                tabview.add("🥧 By Grade")
                self._display_chart_in_tab(tabview.tab("🥧 By Grade"), grade_chart)
            
            self.log_message("Charts displayed successfully")
        except Exception as e:
            messagebox.showerror("Chart Error", f"Could not display charts: {e}")

    def _display_chart_in_tab(self, tab, image_path):
        """Display a chart image in a tab."""
        try:
            if not PILLOW_AVAILABLE or not image_path:
                return
            
            from PIL import Image, ImageTk
            
            # Load and display image
            image = Image.open(image_path)
            # Resize if too large
            max_width, max_height = 950, 600
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(image)
            
            label = ctk.CTkLabel(tab, image=photo, text="")
            label.image = photo  # Keep a reference
            label.pack(padx=12, pady=12, fill="both", expand=True)
        except Exception as e:
            ctk.CTkLabel(tab, text=f"Could not load chart: {e}", text_color="red").pack(padx=12, pady=12)

    def build_log_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        header_row = ctk.CTkFrame(tab, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_row, text="Live Log", font=SUBHEADER_FONT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(header_row, text="Clear", width=80, command=self.clear_log,
                      fg_color="transparent", border_width=1).grid(row=0, column=1, sticky="e")

        card = ctk.CTkFrame(tab, corner_radius=10)
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(card, font=MONO_FONT, wrap="word")
        self.log_text.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        self.log_text.insert("end", "System ready.\n")
        self.log_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Connection / scanning
    # ------------------------------------------------------------------
    def toggle_connection(self):
        if self.serial_handler.connected:
            self.stop_event.set()
            self.serial_handler.disconnect()
            self.status_var.set("Disconnected")
            self.status_dot.configure(text_color=COLOR_DISCONNECTED)
            self.connect_button.configure(text="Connect")
            self.scan_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")
            self.log_message("Disconnected from ESP32.")
            return

        ok, msg = self.serial_handler.connect(self.port_var.get())
        if ok:
            self.status_var.set("Connected")
            self.status_dot.configure(text_color=COLOR_CONNECTED)
            self.connect_button.configure(text="Disconnect")
            self.scan_button.configure(state="normal")
            self.log_message("Connected to ESP32 on " + self.port_var.get())
            self.start_reader_thread()
        else:
            self.status_var.set("Connection failed")
            self.status_dot.configure(text_color=COLOR_DISCONNECTED)
            self.log_message(f"Connection failed: {msg}")

    def _set_connected_ui(self):
        if getattr(self, '_closing', False):
            return
        self.status_var.set("Connected")
        self.status_dot.configure(text_color=COLOR_CONNECTED)
        self.connect_button.configure(text="Disconnect")
        self.scan_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def _set_disconnected_ui(self):
        if getattr(self, '_closing', False):
            return
        self.status_var.set("Disconnected")
        self.status_dot.configure(text_color=COLOR_DISCONNECTED)
        self.connect_button.configure(text="Connect")
        self.scan_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")

    def _set_reconnect_ui(self):
        if getattr(self, '_closing', False):
            return
        self.status_dot.configure(text_color=COLOR_DISCONNECTED)
        self.connect_button.configure(text="Disconnect")
        self.scan_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")

    def start_scan(self):
        if self.enroll_dialog is not None and self.enroll_dialog.winfo_exists():
            self.log_message("Close or cancel the active enrollment before starting scan mode.")
            return

        if not self.serial_handler.connected:
            self.log_message("Please connect first.")
            return
        if cmd_scan(self.serial_handler):
            self.stop_button.configure(state="normal")
            self.log_message("Sent SCAN command to ESP32.")
        else:
            self.log_message("Failed to send SCAN command to ESP32.")

    def stop_scan(self):
        if not self.serial_handler.connected:
            return
        if cmd_stop(self.serial_handler):
            self.stop_button.configure(state="disabled")
            self.log_message("Sent STOP command to ESP32.")
        else:
            self.log_message("Failed to send STOP command to ESP32.")

    def start_reader_thread(self):
        if self.reader_thread and self.reader_thread.is_alive():
            return
        self.stop_event.clear()
        self.reader_thread = threading.Thread(target=self.read_serial_output, daemon=True)
        self.reader_thread.start()

    def read_serial_output(self):
        last_reconnect_count = 0
        while not self.stop_event.is_set():
            line = self.serial_handler.read_line()
            if not self.serial_handler.connected:
                # Check if auto-reconnect is in progress
                if self.serial_handler.reconnect_count > 0:
                    if self.serial_handler.reconnect_count != last_reconnect_count:
                        last_reconnect_count = self.serial_handler.reconnect_count
                        status_text = f"Reconnecting... ({self.serial_handler.reconnect_count}/{RECONNECT_MAX_RETRIES})"
                        self.after(0, lambda text=status_text: self.status_var.set(text))
                        self.after(0, self._set_reconnect_ui)
                else:
                    self.after(0, self._set_disconnected_ui)
                time.sleep(0.2)
                continue

            # Reset reconnect counter on successful connection
            if last_reconnect_count > 0:
                last_reconnect_count = 0
                self.after(0, self._set_connected_ui)

            if line is None:
                time.sleep(0.05)
                continue
            if line:
                self.log_message(f"ESP32: {line}")

    def enroll_sample(self):
        if self.enroll_dialog is not None and self.enroll_dialog.winfo_exists():
            self.enroll_dialog.lift()
            self.enroll_dialog.focus()
            return

        if not self.serial_handler.connected:
            self.log_message("Please connect first.")
            return

        if self.stop_button.cget("state") == "normal":
            if cmd_stop(self.serial_handler):
                self.stop_button.configure(state="disabled")
                self.log_message("Sent STOP command to ESP32 before enrollment.")
            else:
                self.log_message("Failed to stop current scan before enrollment.")
                return

        if cmd_enroll(self.serial_handler):
            self.log_message("Sent ENROLL command to ESP32. The ESP32 will use the next free ID.")
            self.open_enroll_dialog()
        else:
            self.log_message("Failed to send ENROLL command to ESP32.")

    def list_fingerprints(self):
        if self.serial_handler.connected:
            cmd_list(self.serial_handler)
            self.log_message("Sent LIST command to ESP32.")
        else:
            self.log_message("Not connected — showing saved student records only.")
        self.open_students_list_dialog()

    # ------------------------------------------------------------------
    # Enroll popup (profile form + live log side by side)
    # ------------------------------------------------------------------
    def open_enroll_dialog(self):
        if self.enroll_dialog is not None and self.enroll_dialog.winfo_exists():
            self.enroll_dialog.lift()
            self.enroll_dialog.focus()
            return

        self.enroll_completed = False
        self.enroll_ready_to_save = False

        dialog = ctk.CTkToplevel(self)
        dialog.title("Enroll New Fingerprint")
        dialog.geometry("760x480")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=0)
        dialog.grid_columnconfigure(1, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        # --- Left: profile form ---
        form = ctk.CTkFrame(dialog, corner_radius=10, width=300)
        form.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="ns")
        form.grid_propagate(False)
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="New Student Profile", font=SUBHEADER_FONT).grid(
            row=0, column=0, padx=14, pady=(14, 10), sticky="w"
        )

        self.enroll_id_var = ctk.StringVar(value="")
        self.enroll_no_var = ctk.StringVar(value="")
        self.enroll_name_var = ctk.StringVar(value="")
        self.enroll_grade_var = ctk.StringVar(value="")
        self.enroll_section_var = ctk.StringVar(value="")
        self.enroll_status_var = ctk.StringVar(value="Waiting for the sensor… Save is disabled until enrollment completes.")

        ctk.CTkLabel(form, text="Fingerprint ID", font=("Segoe UI", 11), text_color=COLOR_MUTED).grid(
            row=1, column=0, padx=14, pady=(6, 0), sticky="w"
        )
        ctk.CTkEntry(
            form, textvariable=self.enroll_id_var, state="disabled", placeholder_text="assigned by sensor"
        ).grid(row=2, column=0, padx=14, pady=(2, 6), sticky="ew")

        fields = [
            ("Student No.", self.enroll_no_var, "e.g. 2026-0142"),
            ("Name", self.enroll_name_var, "Full name"),
            ("Grade", self.enroll_grade_var, "e.g. 10"),
            ("Section", self.enroll_section_var, "e.g. Diamond"),
        ]
        row = 3
        for label, var, placeholder in fields:
            ctk.CTkLabel(form, text=label, font=("Segoe UI", 11), text_color=COLOR_MUTED).grid(
                row=row, column=0, padx=14, pady=(6, 0), sticky="w"
            )
            ctk.CTkEntry(form, textvariable=var, placeholder_text=placeholder).grid(
                row=row + 1, column=0, padx=14, pady=(2, 6), sticky="ew"
            )
            row += 2

        button_row = ctk.CTkFrame(form, fg_color="transparent")
        button_row.grid(row=row, column=0, padx=14, pady=(8, 6), sticky="ew")
        button_row.grid_columnconfigure((0, 1), weight=1)
        self.enroll_save_button = ctk.CTkButton(
            button_row, text="Save", command=self.save_enroll_profile,
            state="disabled"
        )
        self.enroll_save_button.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(
            button_row, text="Close", command=self.close_enroll_dialog,
            fg_color="transparent", border_width=1
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        ctk.CTkLabel(
            form, textvariable=self.enroll_status_var, text_color=COLOR_MUTED,
            wraplength=260, justify="left"
        ).grid(row=row + 1, column=0, padx=14, pady=(4, 14), sticky="w")

        # --- Right: live log mirror ---
        log_frame = ctk.CTkFrame(dialog, corner_radius=10)
        log_frame.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(log_frame, text="Enrollment Log", font=SUBHEADER_FONT).grid(
            row=0, column=0, padx=14, pady=(14, 8), sticky="w"
        )
        self.enroll_log_text = ctk.CTkTextbox(log_frame, font=MONO_FONT, wrap="word")
        self.enroll_log_text.grid(row=1, column=0, padx=14, pady=(0, 14), sticky="nsew")
        self.enroll_log_text.insert("end", "Waiting for ESP32…\n")

        dialog.protocol("WM_DELETE_WINDOW", self.close_enroll_dialog)
        self.enroll_dialog = dialog

    def save_enroll_profile(self):
        if not self.enroll_ready_to_save:
            self.enroll_status_var.set("Please wait until enrollment completes successfully before saving the profile.")
            return

        fingerprint_id = self.enroll_id_var.get().strip()
        if not fingerprint_id:
            self.enroll_status_var.set("Waiting for the sensor to assign a fingerprint ID first.")
            return
        try:
            fingerprint_id = int(fingerprint_id)
        except ValueError:
            self.enroll_status_var.set("Invalid fingerprint ID.")
            return

        student_no = self.enroll_no_var.get().strip() or f"ID{fingerprint_id}"
        student_name = self.enroll_name_var.get().strip() or f"Student {fingerprint_id}"
        grade = self.enroll_grade_var.get().strip() or "N/A"
        section = self.enroll_section_var.get().strip() or "N/A"

        ok, msg = register_student(fingerprint_id, student_no, student_name, grade, section)
        if ok:
            self.enroll_completed = True
            self.enroll_status_var.set(f"Saved profile for ID {fingerprint_id}.")
            self.refresh_student_list()
            self.refresh_statistics()
            self.log_message(f"Student profile saved: ID {fingerprint_id} - {student_name}")
            if self.enroll_dialog is not None and self.enroll_dialog.winfo_exists():
                self.enroll_dialog.after(500, self.close_enroll_dialog)
        else:
            self.enroll_status_var.set(msg)

    def close_enroll_dialog(self):
        if not self.enroll_completed and self.serial_handler.connected:
            # The ESP32 may still be waiting for a finger to finish the enroll
            # routine it started — cancel it so it doesn't hijack the next
            # scan/attendance read with a leftover enroll request.
            if cmd_stop(self.serial_handler):
                self.log_message("Cancelled enrollment — sent STOP command to ESP32.")
            else:
                self.log_message("Could not send STOP command to ESP32 while cancelling enrollment.")

        if self.enroll_dialog is not None and self.enroll_dialog.winfo_exists():
            self.enroll_dialog.grab_release()
            self.enroll_dialog.destroy()
        self.enroll_dialog = None
        self.enroll_log_text = None
        self.enroll_save_button = None

    def _parse_attendance(self, message):
        """Parse ESP32 output for attendance matches and auto-log them to database.
        
        Firmware outputs two lines per match:
          ID:1
          CONFIDENCE:223
        """
        from config import COOLDOWN_SECONDS
        
        # Look for "ID:N" pattern
        id_match = RE_ID_FOUND.search(message)
        if id_match:
            fingerprint_id = int(id_match.group(1))
            
            # Store detection info (next line will be CONFIDENCE if scan succeeded)
            self.last_fingerprint_id = fingerprint_id
            self.last_id_time = time.time()
            self.last_confidence = 0  # Will be overwritten on next line
            return
        
        # Look for "CONFIDENCE:N" pattern — this completes the match
        confidence_match = RE_CONFIDENCE.search(message)
        if self.last_fingerprint_id is not None and (time.time() - self.last_id_time) > self.ID_TIMEOUT:
            # Stale ID arrived without a confidence line; reset it before handling newer scans.
            self.last_fingerprint_id = None
            self.last_confidence = 0

        if confidence_match and self.last_fingerprint_id is not None:
            fingerprint_id = self.last_fingerprint_id
            confidence = int(confidence_match.group(1))
            self.last_confidence = confidence
            
            # Cooldown logic — track last *logged* separately from last *detected*
            # First scan logs immediately; subsequent scans of the same finger within COOLDOWN_SECONDS are blocked.
            last_logged_times = self.__dict__.get('last_logged_times')
            if last_logged_times is None:
                last_logged_times = {}
                self.__dict__['last_logged_times'] = last_logged_times
            current_time = time.time()
            last_logged_at = last_logged_times.get(fingerprint_id)
            if last_logged_at is None or (current_time - last_logged_at) > COOLDOWN_SECONDS:
                # Log to database regardless of whether a student profile exists.
                try:
                    student = get_student(fingerprint_id)
                    log_attendance(
                        fingerprint_id=fingerprint_id,
                        confidence=confidence,
                        status="Present"
                    )
                    if student:
                        self.log_message(f"✓ Attendance logged: {student.get('student_name', 'Unknown')} (ID {fingerprint_id}, confidence {confidence})")
                    else:
                        self.log_message(f"✓ Attendance logged for unknown fingerprint ID {fingerprint_id} (confidence {confidence})")
                    # Build a lightweight display dict and incrementally add the card to the UI
                    now = datetime.now()
                    rec = {
                        'fingerprint_id': fingerprint_id,
                        'student_no': student.get('student_no') if student else 'N/A',
                        'student_name': student.get('student_name') if student else None,
                        'grade': student.get('grade') if student else 'N/A',
                        'section': student.get('section') if student else 'N/A',
                        'date': now.strftime('%Y-%m-%d'),
                        'time': now.strftime('%H:%M:%S'),
                        'confidence': confidence,
                        'status': 'Present',
                        'has_student_profile': student is not None,
                    }
                    display = format_attendance_display(rec)
                    display['has_student_profile'] = student is not None
                    # Insert the new scan into the current view without rebuilding the entire list.
                    try:
                        today_str = datetime.now().strftime('%Y-%m-%d')
                        attendance_mode = getattr(self, 'attendance_mode', 'Today')
                        attendance_offset = getattr(self, 'attendance_offset', 0)

                        if self.tabview.get() == "📅 Attendance":
                            if attendance_mode == 'Today' and rec['date'] == today_str:
                                self.after(0, lambda d=display: self._build_attendance_card(d, prepend=True))
                            elif attendance_mode == 'Recent' and attendance_offset == 0:
                                self.after(0, lambda d=display: self._build_attendance_card(d, prepend=True))
                        # Otherwise skip incremental insert; user may refresh or load more.
                    except Exception:
                        pass
                    
                    # Update per-fingerprint cooldown tracking
                    last_logged_times[fingerprint_id] = current_time
                except Exception as e:
                    self.log_message(f"Error logging attendance: {e}")
            else:
                # Still within cooldown — silently skip (spam protection)
                pass
            
            # Reset detection state for next scan
            self.last_fingerprint_id = None
            return
        
        # Look for "UNKNOWN" — finger not recognized
        if RE_UNKNOWN.search(message):
            # Rate-limit UNKNOWN logging using a separate global throttle
            # (not per-fingerprint, since all unknowns share the same ID 0)
            try:
                current_time = time.time()
                last_unknown_time = self.__dict__.get('last_unknown_time', None)
                if last_unknown_time is None or (current_time - last_unknown_time) > COOLDOWN_SECONDS:
                    now = datetime.now()
                    log_attendance(0, 0, "UNKNOWN", now)
                    self.log_message(f"⚠ Unknown fingerprint scanned — saved to attendance log ({now.strftime('%Y-%m-%d %H:%M:%S')})")
                    # Refresh the current attendance view to show the new unknown scan
                    rec = {
                        'fingerprint_id': 0,
                        'student_no': 'N/A',
                        'student_name': None,
                        'grade': 'N/A',
                        'section': 'N/A',
                        'date': now.strftime('%Y-%m-%d'),
                        'time': now.strftime('%H:%M:%S'),
                        'confidence': 0,
                        'status': 'UNKNOWN',
                    }
                    display = format_attendance_display(rec)
                    try:
                        today_str = datetime.now().strftime('%Y-%m-%d')
                        attendance_mode = getattr(self, 'attendance_mode', 'Today')
                        attendance_offset = getattr(self, 'attendance_offset', 0)

                        if self.tabview.get() == "📅 Attendance":
                            if attendance_mode == 'Today' and rec['date'] == today_str:
                                self.after(0, lambda d=display: self._build_attendance_card(d, prepend=True))
                            elif attendance_mode == 'Recent' and attendance_offset == 0:
                                self.after(0, lambda d=display: self._build_attendance_card(d, prepend=True))
                    except Exception:
                        pass
                    # Update the global unknown throttle time
                    self.__dict__['last_unknown_time'] = current_time
                else:
                    # Skipped due to cooldown
                    pass
            except Exception as e:
                self.log_message(f"Error saving unknown scan: {e}")
            finally:
                self.last_fingerprint_id = None

    def _parse_enroll_progress(self, message):
        """Watch ESP32 output for enroll-progress lines and reflect them in the popup."""
        if self.enroll_dialog is None or not self.enroll_dialog.winfo_exists():
            return

        match = RE_ENROLLING_AS.search(message)
        if match:
            self.enroll_id_var.set(match.group(1))
            self.enroll_ready_to_save = False
            if self.enroll_save_button is not None:
                self.enroll_save_button.configure(state="disabled")
            self.enroll_status_var.set("Enrolling — follow the prompts on the sensor. Save is disabled until enrollment completes.")
            return

        match = RE_ENROLL_SUCCESS.search(message)
        if match:
            self.enroll_id_var.set(match.group(1))
            self.enroll_ready_to_save = True
            if self.enroll_save_button is not None:
                self.enroll_save_button.configure(state="normal")
            self.enroll_status_var.set(
                f"Fingerprint saved as ID {match.group(1)}. Fill in the student's details and Save."
            )
            return

        if RE_ENROLL_CANCEL.search(message):
            self.enroll_ready_to_save = False
            if self.enroll_save_button is not None:
                self.enroll_save_button.configure(state="disabled")
            self.enroll_status_var.set(
                "Enrollment cancelled. Close this dialog or start a new enrollment to try again."
            )
            return

        upper = message.upper()
        if "ERROR" in upper or "FAIL" in upper:
            self.enroll_status_var.set("Sensor reported an error — check the log on the right.")

    # ------------------------------------------------------------------
    # Wipe popup (confirmation + live log side by side)
    # ------------------------------------------------------------------
    def open_wipe_dialog(self):
        if self.wipe_dialog is not None and self.wipe_dialog.winfo_exists():
            self.wipe_dialog.lift()
            self.wipe_dialog.focus()
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Wipe All Fingerprints")
        dialog.geometry("700x420")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=0)
        dialog.grid_columnconfigure(1, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        # --- Left: warning + confirmation ---
        panel = ctk.CTkFrame(dialog, corner_radius=10, width=280)
        panel.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="ns")
        panel.grid_propagate(False)
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(panel, text="⚠", font=("Segoe UI", 32), text_color=COLOR_DANGER).grid(
            row=0, column=0, padx=14, pady=(20, 4)
        )
        ctk.CTkLabel(panel, text="Wipe All Fingerprints", font=SUBHEADER_FONT).grid(
            row=1, column=0, padx=14, pady=(0, 8)
        )
        ctk.CTkLabel(
            panel,
            text="This erases every fingerprint stored on the sensor AND "
                 "deletes all student profiles from the database. This cannot be undone.",
            text_color=COLOR_MUTED, wraplength=230, justify="left"
        ).grid(row=2, column=0, padx=14, pady=(0, 16), sticky="w")

        self.wipe_status_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            panel, textvariable=self.wipe_status_var, text_color=COLOR_MUTED,
            wraplength=230, justify="left"
        ).grid(row=3, column=0, padx=14, pady=(0, 10), sticky="w")

        button_row = ctk.CTkFrame(panel, fg_color="transparent")
        button_row.grid(row=4, column=0, padx=14, pady=(4, 16), sticky="ew")
        button_row.grid_columnconfigure((0, 1), weight=1)

        self.wipe_confirm_button = ctk.CTkButton(
            button_row, text="Wipe All", command=self.confirm_wipe,
            fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER
        )
        self.wipe_confirm_button.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(
            button_row, text="Close", command=self.close_wipe_dialog,
            fg_color="transparent", border_width=1
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # --- Right: live log mirror ---
        log_frame = ctk.CTkFrame(dialog, corner_radius=10)
        log_frame.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(log_frame, text="Live Log", font=SUBHEADER_FONT).grid(
            row=0, column=0, padx=14, pady=(14, 8), sticky="w"
        )
        self.wipe_log_text = ctk.CTkTextbox(log_frame, font=MONO_FONT, wrap="word")
        self.wipe_log_text.grid(row=1, column=0, padx=14, pady=(0, 14), sticky="nsew")
        self.wipe_log_text.insert("end", "Ready.\n")

        dialog.protocol("WM_DELETE_WINDOW", self.close_wipe_dialog)
        self.wipe_dialog = dialog

    def confirm_wipe(self):
        if not self.serial_handler.connected:
            self.wipe_status_var.set("Please connect first.")
            return

        if not messagebox.askyesno(
            "Wipe All Fingerprints",
            "This will erase every fingerprint on the sensor AND delete every "
            "student profile from the database. This cannot be undone.\n\n"
            "Continue?",
            parent=self.wipe_dialog,
        ):
            return

        if self.wipe_confirm_button is not None and self.wipe_confirm_button.winfo_exists():
            self.wipe_confirm_button.configure(state="disabled")
        self.wipe_status_var.set("Wiping… please wait.")
        if cmd_wipe(self.serial_handler):
            self.log_message("Sent WIPE command to ESP32.")
        else:
            self.wipe_status_var.set("Failed to send WIPE command to ESP32.")
            if self.wipe_confirm_button is not None and self.wipe_confirm_button.winfo_exists():
                self.wipe_confirm_button.configure(state="normal")

    def close_wipe_dialog(self):
        if self.wipe_dialog is not None and self.wipe_dialog.winfo_exists():
            self.wipe_dialog.grab_release()
            self.wipe_dialog.destroy()
        self.wipe_dialog = None
        self.wipe_log_text = None
        self.wipe_status_var = None
        self.wipe_confirm_button = None

    def _parse_wipe_progress(self, message):
        """Watch ESP32 output for wipe-progress lines and reflect them in the popup."""
        if self.wipe_dialog is None or not self.wipe_dialog.winfo_exists():
            return
        if self.wipe_status_var is None:
            return

        if RE_WIPE_START.search(message):
            self.wipe_status_var.set("Wiping… please wait.")
            return

        if RE_WIPE_SUCCESS.search(message):
            student_count, attendance_count = self._clear_database_data()
            self.wipe_status_var.set(
                f"✅ All fingerprints wiped. Cleared {student_count} student profile(s) and {attendance_count} attendance record(s)."
            )
            if self.wipe_confirm_button is not None and self.wipe_confirm_button.winfo_exists():
                self.wipe_confirm_button.configure(state="normal")
            return

        upper = message.upper()
        if "ERROR" in upper or "FAIL" in upper:
            self.wipe_status_var.set("Sensor reported an error — check the log on the right.")
            if self.wipe_confirm_button is not None and self.wipe_confirm_button.winfo_exists():
                self.wipe_confirm_button.configure(state="normal")

    # ------------------------------------------------------------------
    # Student roster popup (opened from "List") + Edit popup
    # ------------------------------------------------------------------
    def open_students_list_dialog(self):
        if self.students_dialog is not None and self.students_dialog.winfo_exists():
            self.students_dialog.lift()
            self.students_dialog.focus()
            self.refresh_student_list()
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Registered Students")
        dialog.geometry("380x520")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(dialog, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Registered Students", font=SUBHEADER_FONT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            header, text="↻", width=28, height=26, fg_color="transparent", border_width=1,
            command=self.refresh_student_list
        ).grid(row=0, column=1, sticky="e")

        self.students_list_frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        self.students_list_frame.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.students_list_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            dialog, text="Close", command=self.close_students_dialog,
            fg_color="transparent", border_width=1
        ).grid(row=2, column=0, padx=16, pady=(0, 16), sticky="ew")

        dialog.protocol("WM_DELETE_WINDOW", self.close_students_dialog)
        self.students_dialog = dialog
        self.refresh_student_list()

    def close_students_dialog(self):
        if self.students_dialog is not None and self.students_dialog.winfo_exists():
            self.students_dialog.grab_release()
            self.students_dialog.destroy()
        self.students_dialog = None
        self.students_list_frame = None

    def _clear_database_data(self):
        """Deletes every student profile and attendance record from the database."""
        student_count, attendance_count = clear_all_data()
        self.refresh_student_list()
        self.refresh_attendance_view()
        self.refresh_statistics()
        if student_count or attendance_count:
            self.log_message(
                f"Cleared {student_count} student profile(s) and {attendance_count} attendance record(s) from the database."
            )
        return student_count, attendance_count

    def refresh_student_list(self):
        """Rebuilds the roster popup's rows, if that popup is currently open."""
        if self.students_list_frame is None or not self.students_list_frame.winfo_exists():
            return

        for child in self.students_list_frame.winfo_children():
            child.destroy()

        students = get_all_students()
        if not students:
            ctk.CTkLabel(
                self.students_list_frame, text="No students yet.",
                text_color=COLOR_MUTED, font=("Segoe UI", 11)
            ).pack(anchor="w", padx=4, pady=8)
            return

        for student in students:
            self._build_student_row(student).pack(fill="x", padx=2, pady=4)

    def _build_student_row(self, student):
        fingerprint_id = student["fingerprint_id"]

        row = ctk.CTkFrame(self.students_list_frame, fg_color="transparent")
        row.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(info, text=student["student_name"], font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            info, text=f"ID {fingerprint_id}  ·  No. {student['student_no']}",
            font=("Segoe UI", 10), text_color=COLOR_MUTED
        ).pack(anchor="w")

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.grid(row=0, column=1, padx=(4, 0), sticky="e")

        ctk.CTkButton(
            actions, text="✎", width=28, height=24, fg_color="transparent", border_width=1,
            command=lambda fid=fingerprint_id: self.open_edit_dialog(fid),
            state="normal" if self.has_permission("enroll") else "disabled"
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            actions, text="🗑", width=28, height=24, fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER,
            command=lambda fid=fingerprint_id: self.delete_student_from_list(fid),
            state="normal" if self.has_permission("delete") else "disabled"
        ).pack(side="left")

        return row

    def delete_student_from_list(self, fingerprint_id, parent=None):
        if parent is None:
            parent = self.students_dialog if self.students_dialog is not None and self.students_dialog.winfo_exists() else self

        if not self.has_permission("delete"):
            messagebox.showerror("Permission Denied", "Your role does not have permission to delete students.", parent=parent)
            return False

        if self.serial_handler.connected:
            if self.enroll_dialog is not None and self.enroll_dialog.winfo_exists():
                messagebox.showwarning(
                    "Delete Disabled",
                    "An enrollment is currently active. Close or cancel enrollment before deleting a fingerprint.",
                    parent=parent
                )
                return False

            if self.stop_button.cget("state") == "normal":
                if messagebox.askyesno(
                    "Stop Scan First",
                    "The ESP32 is currently scanning. Stop scanning before deleting this fingerprint?",
                    parent=parent
                ):
                    if cmd_stop(self.serial_handler):
                        self.stop_button.configure(state="disabled")
                        self.log_message("Sent STOP command to ESP32 before deleting fingerprint.")
                    else:
                        messagebox.showerror(
                            "Delete Error",
                            "Could not stop scan mode on the ESP32. Try again.",
                            parent=parent
                        )
                        return False
                else:
                    return False

        if self.serial_handler.connected:
            warning = (
                f"Delete fingerprint ID {fingerprint_id}?\n\n"
                "This removes the student profile from the database AND "
                "erases this fingerprint from the sensor. This cannot be undone."
            )
        else:
            warning = (
                f"Delete the profile for fingerprint ID {fingerprint_id}?\n\n"
                "The device isn't connected, so only the database record will "
                "be removed. Connect and delete this ID again later to also "
                "clear it from the sensor."
            )

        if not messagebox.askyesno("Delete Student", warning, parent=parent):
            return False

        if self.serial_handler.connected:
            if not cmd_delete(self.serial_handler, fingerprint_id):
                messagebox.showerror(
                    "Delete Error",
                    f"Could not send DELETE:{fingerprint_id} to ESP32.",
                    parent=parent
                )
                return False
            self.log_message(f"Sent DELETE:{fingerprint_id} command to ESP32.")

        delete_student(fingerprint_id)
        self.refresh_student_list()
        self.refresh_statistics()
        self.log_message(f"Deleted student profile for ID {fingerprint_id}.")
        return True

    def open_edit_dialog(self, fingerprint_id):
        student = get_student(fingerprint_id)
        if not student:
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Edit Student — ID {fingerprint_id}")
        dialog.geometry("340x460")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        form = ctk.CTkFrame(dialog, corner_radius=10)
        form.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Student Profile", font=SUBHEADER_FONT).grid(
            row=0, column=0, padx=14, pady=(14, 10), sticky="w"
        )

        id_var = ctk.StringVar(value=str(fingerprint_id))
        no_var = ctk.StringVar(value=student["student_no"])
        name_var = ctk.StringVar(value=student["student_name"])
        grade_var = ctk.StringVar(value=student["grade"])
        section_var = ctk.StringVar(value=student["section"])
        status_var = ctk.StringVar(value="")

        ctk.CTkLabel(form, text="Fingerprint ID", font=("Segoe UI", 11), text_color=COLOR_MUTED).grid(
            row=1, column=0, padx=14, pady=(6, 0), sticky="w"
        )
        ctk.CTkEntry(form, textvariable=id_var, state="disabled").grid(
            row=2, column=0, padx=14, pady=(2, 6), sticky="ew"
        )

        fields = [
            ("Student No.", no_var, "e.g. 2026-0142"),
            ("Name", name_var, "Full name"),
            ("Grade", grade_var, "e.g. 10"),
            ("Section", section_var, "e.g. Diamond"),
        ]
        row = 3
        for label, var, placeholder in fields:
            ctk.CTkLabel(form, text=label, font=("Segoe UI", 11), text_color=COLOR_MUTED).grid(
                row=row, column=0, padx=14, pady=(6, 0), sticky="w"
            )
            ctk.CTkEntry(form, textvariable=var, placeholder_text=placeholder).grid(
                row=row + 1, column=0, padx=14, pady=(2, 6), sticky="ew"
            )
            row += 2

        def do_save():
            student_no = no_var.get().strip() or f"ID{fingerprint_id}"
            student_name = name_var.get().strip() or f"Student {fingerprint_id}"
            grade = grade_var.get().strip() or "N/A"
            section = section_var.get().strip() or "N/A"
            ok, msg = register_student(fingerprint_id, student_no, student_name, grade, section)
            if ok:
                status_var.set("Saved.")
                self.refresh_student_list()
                self.refresh_statistics()
                self.log_message(f"Student profile updated: ID {fingerprint_id} - {student_name}")
                dialog.after(400, dialog.destroy)
            else:
                status_var.set(msg)

        def do_delete():
            if self.delete_student_from_list(fingerprint_id, parent=dialog):
                dialog.destroy()

        button_row = ctk.CTkFrame(form, fg_color="transparent")
        button_row.grid(row=row, column=0, padx=14, pady=(8, 6), sticky="ew")
        button_row.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(
            button_row, text="Save", command=do_save,
            state="normal" if self.has_permission("enroll") else "disabled"
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(
            button_row, text="Delete", command=do_delete,
            fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER,
            state="normal" if self.has_permission("delete") else "disabled"
        ).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(
            button_row, text="Close", command=dialog.destroy,
            fg_color="transparent", border_width=1
        ).grid(row=0, column=2, padx=(4, 0), sticky="ew")

        ctk.CTkLabel(
            form, textvariable=status_var, text_color=COLOR_MUTED, wraplength=260, justify="left"
        ).grid(row=row + 1, column=0, padx=14, pady=(4, 14), sticky="w")

    def backup_database(self):
        """Create a database backup."""
        try:
            success, message, path = backup_database_service()
            if success:
                self.log_message(f"✓ {message}")
                messagebox.showinfo("Backup Successful", f"{message}\n\nBackup saved at:\n{path}")
            else:
                self.log_message(f"✗ Backup failed: {message}")
                messagebox.showerror("Backup Failed", message)
        except Exception as e:
            self.log_message(f"✗ Error: {e}")
            messagebox.showerror("Error", f"Backup error: {e}")

    def open_restore_dialog(self):
        """Open a dialog to restore the database from an existing backup."""
        if not self.has_permission("restore"):
            messagebox.showerror("Permission Denied", "Your role cannot restore backups.", parent=self)
            return

        # Avoid opening multiple restore dialogs
        if hasattr(self, 'restore_dialog') and self.restore_dialog is not None and self.restore_dialog.winfo_exists():
            self.restore_dialog.lift()
            self.restore_dialog.focus()
            return

        backups = list_backups()
        if not backups:
            messagebox.showinfo("No Backups", "No database backup files were found.", parent=self)
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Restore Database")
        dialog.geometry("720x520")
        dialog.transient(self)
        dialog.grab_set()
        self.restore_dialog = dialog
        dialog.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, 'restore_dialog', None), dialog.destroy()))
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        content = ctk.CTkFrame(dialog, corner_radius=10)
        content.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(content, text="Restore Database Backup", font=SUBHEADER_FONT).grid(
            row=0, column=0, padx=14, pady=(14, 8), sticky="w"
        )

        list_frame = ctk.CTkScrollableFrame(content, fg_color="transparent", corner_radius=10)
        list_frame.grid(row=1, column=0, padx=14, pady=(0, 14), sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)

        for i, backup in enumerate(backups):
            row = ctk.CTkFrame(list_frame, fg_color="transparent", corner_radius=8)
            row.grid_columnconfigure(0, weight=1)
            row.grid(row=i, column=0, padx=8, pady=8, sticky="ew")

            label = (
                f"{backup['name']}\n"
                f"Date: {backup['date']}  ·  Size: {backup['size_mb']}"
            )
            ctk.CTkLabel(row, text=label, justify="left", anchor="w").grid(
                row=0, column=0, padx=12, pady=12, sticky="w"
            )
            ctk.CTkButton(
                row, text="Restore", width=100,
                command=lambda path=backup['path']: self._confirm_restore(path, dialog)
            ).grid(row=0, column=1, padx=12, pady=12, sticky="e")

        ctk.CTkButton(
            content, text="Close", width=120, fg_color="transparent", border_width=1,
            command=dialog.destroy
        ).grid(row=2, column=0, padx=14, pady=(0, 14), sticky="e")

    def _confirm_restore(self, backup_path, parent):
        if not messagebox.askyesno(
            "Confirm Restore",
            "Restoring a backup will overwrite the current attendance database. Continue?",
            parent=parent
        ):
            return

        # If scanning is active, ask to stop first to avoid DB races
        try:
            if getattr(self, 'stop_button', None) is not None and self.stop_button.cget("state") == "normal":
                if messagebox.askyesno("Stop Scan", "A scan is currently running. Stop it before restoring?", parent=parent):
                    if not cmd_stop(self.serial_handler):
                        messagebox.showerror("Error", "Could not stop the current scan. Aborting restore.", parent=parent)
                        return
                    # allow a small pause for the ESP32 to settle
                    time.sleep(0.2)
                else:
                    return

        except Exception:
            pass

        success, message = restore_database(backup_path)
        if success:
            self.log_message(f"Database restored from backup: {Path(backup_path).name}")
            messagebox.showinfo("Restore Successful", message, parent=parent)
            self.init_database()
            self.refresh_student_list()
            self.refresh_attendance_view()
            self.refresh_statistics()
            parent.destroy()
            try:
                setattr(self, 'restore_dialog', None)
            except Exception:
                pass
        else:
            messagebox.showerror("Restore Failed", message, parent=parent)
            try:
                setattr(self, 'restore_dialog', None)
            except Exception:
                pass

    def quit_app(self):
        if getattr(self, "_closing", False):
            return
        self._closing = True
        self.stop_event.set()
        if self.serial_handler.connected:
            try:
                self.serial_handler.disconnect()
            except Exception:
                pass
        if self.winfo_exists():
            self.destroy()

    def _ui_ready(self):
        try:
            return not getattr(self, "_closing", False) and self.winfo_exists()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Attendance / log
    # ------------------------------------------------------------------
    def toggle_attendance_view(self):
        self.refresh_attendance_view()

    def refresh_attendance_view(self):
        if not self._ui_ready():
            return
        # Fetch records according to the current view mode
        if getattr(self, 'attendance_mode', 'Today') == 'Today':
            records = get_attendance_today()
            # When switching to Today view ensure offset is reset
            self.attendance_offset = 0
        else:
            records = get_attendance_paginated(limit=self.attendance_page_size, offset=self.attendance_offset)
        # Rebuild the entire view (used for manual refresh). Keep per-record errors isolated
        for child in self.attendance_scroll.winfo_children():
            child.destroy()

        if not records:
            ctk.CTkLabel(
                self.attendance_scroll,
                text="No attendance records yet.",
                text_color=COLOR_MUTED,
                font=("Segoe UI", 12),
                anchor="w"
            ).pack(anchor="w", padx=4, pady=8)
            return

        for record in records:
            try:
                fid = record.get('fingerprint_id')
                has_student_profile = False
                if fid not in (None, 0):
                    has_student_profile = get_student(fid) is not None
                display = format_attendance_display(record)
                display['has_student_profile'] = has_student_profile
                self._build_attendance_card(display, prepend=False)
            except Exception as e:
                # Log and skip a single bad row rather than breaking the whole view
                self.log_message(f"Error rendering attendance row: {e}")

        # Update Load More visibility (enable only for Recent mode)
        self._update_load_more_visibility()

    def load_more_attendance(self):
        """Load the next page of recent attendance records and append them."""
        if getattr(self, 'attendance_mode', 'Today') != 'Recent':
            return
        self.attendance_offset += self.attendance_page_size
        try:
            rows = get_attendance_paginated(limit=self.attendance_page_size, offset=self.attendance_offset)
            if not rows:
                # No more rows; disable button
                button = getattr(self, 'load_more_button', None)
                if button is not None:
                    button.configure(state='disabled')
                return
            for record in rows:
                fid = record.get('fingerprint_id')
                has_student_profile = False
                if fid not in (None, 0):
                    has_student_profile = get_student(fid) is not None
                display = format_attendance_display(record)
                display['has_student_profile'] = has_student_profile
                self._build_attendance_card(display, prepend=False)
            # Disable button if fewer than page_size rows were returned (end of data)
            if len(rows) < self.attendance_page_size:
                button = getattr(self, 'load_more_button', None)
                if button is not None:
                    button.configure(state='disabled')
        except Exception as e:
            self.log_message(f"Error loading more attendance: {e}")

    def _build_attendance_card(self, display: dict, prepend: bool = True):
        """Create one attendance card for a single `display` dict and insert it into the scroll area.

        If `prepend` is True the card is inserted at the top; otherwise appended in order.
        """
        card = ctk.CTkFrame(self.attendance_scroll, corner_radius=10)
        card.grid_columnconfigure(1, weight=1)

        # Left: avatar/status
        left = ctk.CTkFrame(card, width=56, fg_color="transparent")
        left.grid(row=0, column=0, rowspan=3, padx=(8, 4), pady=8, sticky="nsw")
        left.grid_propagate(False)

        name = display.get('student_name', '') or ''
        initials = "".join([p[0] for p in name.split() if p])[:2].upper() if name else "--"
        avatar = ctk.CTkLabel(left, text=initials, width=40, height=40, corner_radius=20,
                               fg_color="#3b3b3b", font=("Segoe UI", 12, "bold"))
        avatar.pack(pady=(6, 4))

        status_text = str(display.get('status', '')).upper()
        if status_text.startswith('GOOD') or status_text == 'PRESENT':
            status_color = COLOR_CONNECTED
        elif status_text.startswith('WEAK'):
            status_color = "#f59e0b"
        else:
            status_color = COLOR_DANGER
        status_badge = ctk.CTkFrame(left, width=40, height=14, corner_radius=8, fg_color=status_color)
        status_badge.pack(pady=(0, 6))

        # Main content
        ctk.CTkLabel(
            card,
            text=f"{display.get('student_name')} · ID {display.get('fingerprint_id')}",
            font=("Segoe UI", 13, "bold"),
            anchor="w"
        ).grid(row=0, column=1, padx=(4, 12), pady=(10, 2), sticky="w")

        ctk.CTkLabel(
            card,
            text=f"No: {display.get('student_no')} · Grade: {display.get('grade')} · Section: {display.get('section')}",
            text_color=COLOR_MUTED,
            anchor="w"
        ).grid(row=1, column=1, padx=(4, 12), pady=2, sticky="w")

        # Right area: actions or confidence
        fid = display.get('fingerprint_id')
        if fid != 0 and not display.get('has_student_profile', False):
            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.grid(row=0, column=2, rowspan=3, padx=(0, 12), pady=8, sticky="ne")
            actions.grid_columnconfigure(0, weight=1)
            add_btn = ctk.CTkButton(actions, text="➕ Add Student", width=120, command=lambda fid=fid: self.open_add_student_dialog(fid))
            add_btn.grid(row=0, column=0, pady=(8, 4), sticky="e")

            def _show_unknown_details(rec=display):
                dlg = ctk.CTkToplevel(self)
                dlg.title("Unregistered Scan")
                dlg.geometry("360x160")
                dlg.transient(self)
                dlg.grab_set()
                ctk.CTkLabel(dlg, text=f"Unregistered scan", font=SUBHEADER_FONT).pack(pady=(12, 6))
                ctk.CTkLabel(dlg, text=f"Date: {rec.get('date')} {rec.get('time')}", text_color=COLOR_MUTED).pack()
                ctk.CTkLabel(dlg, text=f"Status: {rec.get('status')}  Confidence: {rec.get('confidence')}", text_color=COLOR_MUTED).pack()
                ctk.CTkButton(dlg, text="Close", command=dlg.destroy).pack(pady=(12, 8))

            view_btn = ctk.CTkButton(actions, text="🔎 View", width=120, command=_show_unknown_details)
            view_btn.grid(row=1, column=0, pady=(0, 8), sticky="e")
        else:
            try:
                conf_val = int(display.get('confidence', 0))
            except Exception:
                conf_val = 0
            conf_text = f"Confidence: {display.get('confidence')}"
            conf_color = COLOR_CONNECTED if conf_val >= 150 else "#f59e0b"
            conf_label = ctk.CTkLabel(card, text=conf_text, fg_color=conf_color, corner_radius=8, width=160)
            conf_label.grid(row=0, column=2, rowspan=2, padx=(0, 12), pady=(12, 0), sticky="e")

        ctk.CTkLabel(
            card,
            text=f"{display.get('date')} {display.get('time')} · Status: {display.get('status')}",
            text_color=COLOR_MUTED,
            anchor="w"
        ).grid(row=2, column=1, padx=(4, 12), pady=(2, 10), sticky="w")

        # Insert at the top if requested
        children = self.attendance_scroll.winfo_children()
        if prepend and children:
            card.pack(fill="x", padx=2, pady=6, before=children[0])
        else:
            card.pack(fill="x", padx=2, pady=6)

    def open_add_student_dialog(self, fingerprint_id: int):
        """Open a modal to add a student profile for an existing fingerprint ID.

        This is like Edit but assumes no student row exists yet and Save is enabled immediately.
        """
        if fingerprint_id is None or int(fingerprint_id) <= 0:
            messagebox.showerror("Invalid Fingerprint ID", "Only real fingerprint IDs can be registered as students.", parent=self)
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Add Student — ID {fingerprint_id}")
        dialog.geometry("340x460")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        form = ctk.CTkFrame(dialog, corner_radius=10)
        form.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Student Profile", font=SUBHEADER_FONT).grid(
            row=0, column=0, padx=14, pady=(14, 10), sticky="w"
        )

        id_var = ctk.StringVar(value=str(fingerprint_id))
        no_var = ctk.StringVar(value="")
        name_var = ctk.StringVar(value="")
        grade_var = ctk.StringVar(value="")
        section_var = ctk.StringVar(value="")
        status_var = ctk.StringVar(value="")

        ctk.CTkLabel(form, text="Fingerprint ID", font=("Segoe UI", 11), text_color=COLOR_MUTED).grid(
            row=1, column=0, padx=14, pady=(6, 0), sticky="w"
        )
        ctk.CTkEntry(form, textvariable=id_var, state="disabled").grid(
            row=2, column=0, padx=14, pady=(2, 6), sticky="ew"
        )

        fields = [
            ("Student No.", no_var, "Leave blank to use ID{fingerprint_id}"),
            ("Name", name_var, "Full name"),
            ("Grade", grade_var, "e.g. 10"),
            ("Section", section_var, "e.g. Diamond"),
        ]
        row = 3
        for label, var, placeholder in fields:
            ctk.CTkLabel(form, text=label, font=("Segoe UI", 11), text_color=COLOR_MUTED).grid(
                row=row, column=0, padx=14, pady=(6, 0), sticky="w"
            )
            ctk.CTkEntry(form, textvariable=var, placeholder_text=placeholder).grid(
                row=row + 1, column=0, padx=14, pady=(2, 6), sticky="ew"
            )
            row += 2

        def do_save():
            student_no = no_var.get().strip() or f"ID{fingerprint_id}"
            student_name = name_var.get().strip() or f"Student {fingerprint_id}"
            grade = grade_var.get().strip() or "N/A"
            section = section_var.get().strip() or "N/A"
            ok, msg = register_student(fingerprint_id, student_no, student_name, grade, section)
            if ok:
                status_var.set("Saved.")
                self.refresh_student_list()
                self.refresh_statistics()
                self.log_message(f"Student profile created: ID {fingerprint_id} - {student_name}")
                dialog.after(400, dialog.destroy)
                # Refresh attendance view to show updated name for any recent cards
                self.refresh_attendance_view()
            else:
                status_var.set(msg)

        button_row = ctk.CTkFrame(form, fg_color="transparent")
        button_row.grid(row=row, column=0, padx=14, pady=(8, 6), sticky="ew")
        button_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            button_row, text="Save", command=do_save,
            state="normal" if self.has_permission("enroll") else "disabled"
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(
            button_row, text="Close", command=dialog.destroy,
            fg_color="transparent", border_width=1
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

    def log_message(self, message):
        if self._ui_ready():
            self.after(0, self._append_log_message, message)

    def _append_log_message(self, message):
        if not self._ui_ready():
            return

        for widget in (
            getattr(self, "log_text", None),
            getattr(self, "enroll_log_text", None),
            getattr(self, "wipe_log_text", None),
        ):
            if widget is None:
                continue
            try:
                if widget.winfo_exists():
                    widget.configure(state="normal")
                    widget.insert("end", message + "\n")
                    widget.see("end")
                    widget.configure(state="disabled")
            except Exception:
                pass

        try:
            raw_message = message
            if isinstance(message, str) and message.startswith("ESP32:"):
                raw_message = message[len("ESP32:"):].strip()
            self._parse_attendance(raw_message)
            self._parse_enroll_progress(raw_message)
            self._parse_wipe_progress(raw_message)
        except Exception:
            pass

    def clear_log(self):
        if not self._ui_ready():
            return
        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.insert("end", "Log cleared.\n")
            self.log_text.configure(state="disabled")
        except Exception:
            pass


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = FingerprintApp()
    app.mainloop()


if __name__ == "__main__":
    main()