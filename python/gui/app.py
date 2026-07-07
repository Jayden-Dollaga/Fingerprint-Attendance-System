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

from config import COM_PORT, BAUD_RATE, BAUD_RATES, RECONNECT_MAX_RETRIES
from core.serial_handler import SerialHandler
from settings_store import default_settings, load_settings, save_settings
from core.commands import cmd_scan, cmd_stop, cmd_enroll, cmd_delete, cmd_wipe, cmd_list
from gui.sidebar import build_sidebar
from gui.attendance_page import AttendancePage, build_attendance_tab, refresh_attendance_view, load_more_attendance, build_attendance_card
from gui.statistics_page import build_statistics_tab
from gui.log_page import build_log_tab
from gui.settings_dialog import open_settings_dialog
from gui.dialogs import open_enroll_dialog, save_enroll_profile, close_enroll_dialog, open_wipe_dialog, confirm_wipe, close_wipe_dialog, open_restore_dialog
from gui import reports_page
from gui.students_page import (
    StudentsPage,
    open_students_list_dialog,
    refresh_student_list,
    delete_student_from_list,
    open_edit_dialog,
    open_add_student_dialog,
)
from gui.dashboard import DashboardPage
from gui.settings_page import SettingsPage
from gui.theme import apply_default_theme
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
        self.geometry("1440x900")
        self.minsize(1200, 760)

        self.serial_handler = SerialHandler()
        self.stop_event = threading.Event()
        self.settings = load_settings()
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
        self.last_unknown_time = 0             # Tracks the last unknown scan time for throttling

        # User role system
        from config import DEFAULT_USER_ROLE
        self.current_role = DEFAULT_USER_ROLE

        self.dashboard_page = DashboardPage(self)
        self.students_page = StudentsPage(self)
        self.attendance_page = AttendancePage(self)
        self.settings_page = SettingsPage(self)

        self._apply_saved_settings()
        self.init_database()
        self.build_ui()

    def init_database(self):
        init_database()

    def _apply_saved_settings(self):
        self.settings = load_settings()
        self.port_var = None
        self.baud_var = None
        self._apply_settings_to_runtime()

    def _apply_settings_to_runtime(self):
        settings = self.settings or default_settings()
        if settings.get("theme"):
            try:
                ctk.set_appearance_mode("Dark" if str(settings["theme"]).lower() == "dark" else "Light")
            except Exception:
                pass
        self.serial_handler.auto_reconnect_enabled = bool(settings.get("auto_reconnect", True))

    def save_current_settings(self):
        settings = {
            "com_port": self.port_var.get().strip() if getattr(self, "port_var", None) else self.settings.get("com_port", ""),
            "baud_rate": int(self.baud_var.get()) if getattr(self, "baud_var", None) and self.baud_var.get() else self.settings.get("baud_rate", BAUD_RATE),
            "cooldown": self.settings.get("cooldown", 10),
            "theme": "dark" if ctk.get_appearance_mode().lower() == "dark" else "light",
            "auto_reconnect": self.serial_handler.auto_reconnect_enabled,
        }
        self.settings = settings
        save_settings(settings)
        return settings

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
        self.refresh_serial_ports(initial=True)

    def build_sidebar(self):
        return build_sidebar(self)

    def switch_page(self, page_name: str):
        if page_name == "dashboard":
            self.dashboard_page.refresh()
        elif page_name == "students":
            self.students_page.refresh()
        elif page_name == "settings":
            self.settings_page.refresh()

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

        self.attendance_page.build(self.tabview.tab("📅 Attendance"))
        build_statistics_tab(self, self.tabview.tab("📊 Statistics"))
        build_log_tab(self, self.tabview.tab("🖥 Live Log"))

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

    def refresh_statistics(self):
        """Refresh the statistics display."""
        if not self._ui_ready():
            return

        try:
            statistics_tab = self.tabview.tab("📊 Statistics")
            for child in statistics_tab.winfo_children():
                child.destroy()
            build_statistics_tab(self, statistics_tab)
            self.tabview.set("📊 Statistics")
            self.log_message("Statistics refreshed")
        except Exception as e:
            self.log_message(f"Could not refresh statistics: {e}")

    def show_statistics_report(self):
        reports_page.show_statistics_report(self)

    def export_statistics_report(self):
        reports_page.export_statistics_report(self)

    def show_statistics_charts(self):
        reports_page.show_statistics_charts(self)

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

        port = self.port_var.get().strip()
        if not port:
            self.log_message("Please choose a COM port before connecting.")
            return

        try:
            baud = int(self.baud_var.get())
        except Exception:
            baud = BAUD_RATE

        self.save_current_settings()

        ok, msg = self.serial_handler.connect(port, baud)
        if ok:
            self.status_var.set("Connected")
            self.status_dot.configure(text_color=COLOR_CONNECTED)
            self.connect_button.configure(text="Disconnect")
            self.scan_button.configure(state="normal")
            self.log_message(f"Connected to ESP32 on {port} at {baud} baud")
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

    def refresh_serial_ports(self, initial: bool = False):
        try:
            ports = self.serial_handler.list_available_ports() or []
            current_value = ""
            if hasattr(self, "port_var"):
                current_value = self.port_var.get().strip() if self.port_var.get() else ""

            if ports:
                if current_value not in ports:
                    current_value = ports[0]
                    if hasattr(self, "port_var"):
                        self.port_var.set(current_value)
                if hasattr(self, "port_combobox"):
                    self.port_combobox.configure(values=ports)
                if initial and hasattr(self, "port_var") and self.port_var.get() not in ports:
                    self.port_var.set(ports[0])
            else:
                fallback = current_value or "COM5"
                if hasattr(self, "port_combobox"):
                    self.port_combobox.configure(values=[fallback])
            if not initial:
                self.log_message(f"Serial ports refreshed: {', '.join(ports) if ports else 'none found'}")
        except Exception as e:
            self.log_message(f"Could not refresh serial ports: {e}")

    def open_settings_dialog(self):
        open_settings_dialog(self)

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

        student_count = len(get_all_students())
        self.log_message(f"{student_count} fingerprint(s) registered.")
        self.open_students_list_dialog()

    # ------------------------------------------------------------------
    # Enroll popup (profile form + live log side by side)
    # ------------------------------------------------------------------
    def open_enroll_dialog(self):
        return open_enroll_dialog(self)
    def save_enroll_profile(self):
        return save_enroll_profile(self)

    def close_enroll_dialog(self):
        return close_enroll_dialog(self)
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
            self.__dict__['last_fingerprint_id'] = fingerprint_id
            self.__dict__['last_id_time'] = time.time()
            self.__dict__['last_confidence'] = 0  # Will be overwritten on next line
            return
        
        # Look for "CONFIDENCE:N" pattern — this completes the match
        confidence_match = RE_CONFIDENCE.search(message)
        last_fingerprint_id = self.__dict__.get('last_fingerprint_id')
        last_id_time = self.__dict__.get('last_id_time', 0)
        id_timeout = self.__dict__.get('ID_TIMEOUT', 2.0)
        if last_fingerprint_id is not None and (time.time() - last_id_time) > id_timeout:
            # Stale ID arrived without a confidence line; reset it before handling newer scans.
            self.__dict__['last_fingerprint_id'] = None
            self.__dict__['last_confidence'] = 0
            last_fingerprint_id = None

        if confidence_match and last_fingerprint_id is not None:
            fingerprint_id = last_fingerprint_id
            confidence = int(confidence_match.group(1))
            self.__dict__['last_confidence'] = confidence
            
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
                                self.after(0, lambda d=display: build_attendance_card(self, d, prepend=True))
                            elif attendance_mode == 'Recent' and attendance_offset == 0:
                                self.after(0, lambda d=display: build_attendance_card(self, d, prepend=True))
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
                                self.after(0, lambda d=display: build_attendance_card(self, d, prepend=True))
                            elif attendance_mode == 'Recent' and attendance_offset == 0:
                                self.after(0, lambda d=display: build_attendance_card(self, d, prepend=True))
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
        return open_wipe_dialog(self)
    def confirm_wipe(self):
        return confirm_wipe(self)

    def close_wipe_dialog(self):
        return close_wipe_dialog(self)
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
        return open_students_list_dialog(self)
    def close_students_dialog(self):
        return close_students_dialog(self)


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
        return self.students_page.refresh()

    def delete_student_from_list(self, fingerprint_id, parent=None):
        return self.students_page.delete_student(fingerprint_id, parent=parent)
    def open_edit_dialog(self, fingerprint_id):
        return self.students_page.open_edit_dialog(fingerprint_id)

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
        return open_restore_dialog(self)
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
        return self.attendance_page.refresh()
    def load_more_attendance(self):
        return self.attendance_page.load_more()


    def _build_attendance_card(self, display: dict, prepend: bool = True):
        return build_attendance_card(self, display, prepend)

    def open_add_student_dialog(self, fingerprint_id: int):
        return self.students_page.open_add_student_dialog(fingerprint_id)

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
    apply_default_theme(None)
    app = FingerprintApp()
    app.mainloop()


if __name__ == "__main__":
    main()
