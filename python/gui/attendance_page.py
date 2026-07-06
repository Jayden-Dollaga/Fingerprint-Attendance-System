import customtkinter as ctk

from core.utils import format_attendance_display
from services.attendance_service import AttendanceService
from services.student_service import StudentService

COLOR_MUTED = "#8b8b8b"


class AttendancePage:
    def __init__(self, app):
        self.app = app
        self.attendance_service = AttendanceService()
        self.student_service = StudentService()
        self.scroll_frame = None
        self.page_size = 100
        self.offset = 0
        self.mode = "Today"
        self.load_more_button = None

    def build(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        header_row = ctk.CTkFrame(tab, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_row, text="Attendance Records", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.app.attendance_mode_var = ctk.StringVar(value="Today")
        self.app.attendance_mode = "Today"
        mode_menu = ctk.CTkOptionMenu(
            header_row,
            values=["Today", "Recent"],
            variable=self.app.attendance_mode_var,
            command=self.app._on_attendance_mode_changed,
        )
        mode_menu.grid(row=0, column=1, sticky="e", padx=(0, 8))

        self.app.refresh_button = ctk.CTkButton(
            header_row,
            text="↻ Refresh",
            width=100,
            command=self.refresh,
        )
        self.app.refresh_button.grid(row=0, column=2, sticky="e")

        card = ctk.CTkFrame(tab, corner_radius=10)
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)

        self.scroll_frame = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.scroll_frame.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.app.attendance_page_size = self.page_size
        self.app.attendance_offset = self.offset

        self.load_more_button = ctk.CTkButton(card, text="Load more", command=self.load_more)
        self.load_more_button.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 12))
        self.app.load_more_button = self.load_more_button

        self.refresh()
        self.app._update_load_more_visibility()
        return self.scroll_frame

    def refresh(self):
        if not self.app._ui_ready():
            return

        if getattr(self.app, 'attendance_mode', 'Today') == 'Today':
            records = self.attendance_service.get_today()
            self.app.attendance_offset = 0
        else:
            records = self.attendance_service.get_paginated(limit=self.page_size, offset=self.app.attendance_offset)

        for child in self.scroll_frame.winfo_children():
            child.destroy()

        if not records:
            ctk.CTkLabel(
                self.scroll_frame,
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
                    has_student_profile = self.student_service.get_student(fid) is not None
                display = format_attendance_display(record)
                display['has_student_profile'] = has_student_profile
                self.build_card(display, prepend=False)
            except Exception as e:
                self.app.log_message(f"Error rendering attendance row: {e}")

        self.app._update_load_more_visibility()

    def load_more(self):
        if getattr(self.app, 'attendance_mode', 'Today') != 'Recent':
            return
        self.app.attendance_offset += self.page_size
        try:
            rows = self.attendance_service.get_paginated(limit=self.page_size, offset=self.app.attendance_offset)
            if not rows:
                if self.load_more_button is not None:
                    self.load_more_button.configure(state='disabled')
                return
            for record in rows:
                fid = record.get('fingerprint_id')
                has_student_profile = False
                if fid not in (None, 0):
                    has_student_profile = self.student_service.get_student(fid) is not None
                display = format_attendance_display(record)
                display['has_student_profile'] = has_student_profile
                self.build_card(display, prepend=False)
            if len(rows) < self.page_size and self.load_more_button is not None:
                self.load_more_button.configure(state='disabled')
        except Exception as e:
            self.app.log_message(f"Error loading more attendance: {e}")

    def build_card(self, display: dict, prepend: bool = True):
        card = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        card.grid_columnconfigure(1, weight=1)

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
            status_color = "#2ecc71"
        elif status_text.startswith('WEAK'):
            status_color = "#f59e0b"
        else:
            status_color = "#e74c3c"
        status_badge = ctk.CTkFrame(left, width=40, height=14, corner_radius=8, fg_color=status_color)
        status_badge.pack(pady=(0, 6))

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

        fid = display.get('fingerprint_id')
        if fid != 0 and not display.get('has_student_profile', False):
            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.grid(row=0, column=2, rowspan=3, padx=(0, 12), pady=8, sticky="ne")
            actions.grid_columnconfigure(0, weight=1)
            add_btn = ctk.CTkButton(actions, text="➕ Add Student", width=120,
                                    command=lambda fid=fid: self.app.open_add_student_dialog(fid))
            add_btn.grid(row=0, column=0, pady=(8, 4), sticky="e")

            def _show_unknown_details(rec=display):
                dlg = ctk.CTkToplevel(self.app)
                dlg.title("Unregistered Scan")
                dlg.geometry("360x160")
                dlg.transient(self.app)
                dlg.grab_set()
                ctk.CTkLabel(dlg, text="Unregistered scan", font=("Segoe UI", 13, "bold")).pack(pady=(12, 6))
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
            conf_color = "#2ecc71" if conf_val >= 150 else "#f59e0b"
            conf_label = ctk.CTkLabel(card, text=conf_text, fg_color=conf_color, corner_radius=8, width=160)
            conf_label.grid(row=0, column=2, rowspan=2, padx=(0, 12), pady=(12, 0), sticky="e")

        ctk.CTkLabel(
            card,
            text=f"{display.get('date')} {display.get('time')} · Status: {display.get('status')}",
            text_color=COLOR_MUTED,
            anchor="w"
        ).grid(row=2, column=1, padx=(4, 12), pady=(2, 10), sticky="w")

        children = self.scroll_frame.winfo_children()
        if prepend and children:
            card.pack(fill="x", padx=2, pady=6, before=children[0])
        else:
            card.pack(fill="x", padx=2, pady=6)


def build_attendance_tab(app, tab):
    return AttendancePage(app).build(tab)


def refresh_attendance_view(app):
    page = getattr(app, 'attendance_page', None)
    if page is None:
        page = AttendancePage(app)
        app.attendance_page = page
    return page.refresh()


def load_more_attendance(app):
    page = getattr(app, 'attendance_page', None)
    if page is None:
        page = AttendancePage(app)
        app.attendance_page = page
    return page.load_more()


def build_attendance_card(app, display: dict, prepend: bool = True):
    page = getattr(app, 'attendance_page', None)
    if page is None:
        page = AttendancePage(app)
        app.attendance_page = page
    return page.build_card(display, prepend=prepend)
