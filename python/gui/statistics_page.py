import customtkinter as ctk
from datetime import datetime

from core.database import get_all_students, get_attendance_all, count_attendance_by_date
from core.database import generate_statistics_report, generate_attendance_chart, generate_section_chart, generate_grade_chart
from core.database import get_attendance_today
from core.database import get_all_students


def build_statistics_tab(app, tab):
    tab.grid_columnconfigure(0, weight=1)
    tab.grid_rowconfigure(0, weight=0)
    tab.grid_rowconfigure(1, weight=1)

    header_row = ctk.CTkFrame(tab, fg_color="transparent")
    header_row.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    header_row.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(header_row, text="Attendance Statistics Dashboard", font=("Segoe UI", 13, "bold")).grid(
        row=0, column=0, sticky="w"
    )
    ctk.CTkButton(header_row, text="↻ Refresh", width=100, command=app.refresh_statistics).grid(
        row=0, column=1, sticky="e"
    )

    stats_frame = ctk.CTkFrame(tab, corner_radius=0)
    stats_frame.grid(row=1, column=0, sticky="nsew")
    stats_frame.grid_columnconfigure(0, weight=1)
    stats_frame.grid_rowconfigure(0, weight=1)

    scrollable = ctk.CTkScrollableFrame(stats_frame, fg_color="transparent")
    scrollable.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
    scrollable.grid_columnconfigure(0, weight=1)
    scrollable.grid_columnconfigure((0, 1), weight=1)

    metrics_data = [
        ("Total Students", lambda: str(len(get_all_students())), "#3b82f6"),
        ("Total Attendance Logs", lambda: str(len(get_attendance_all())), "#3b82f6"),
    ]

    for i, (label, value_fn, color) in enumerate(metrics_data):
        card = ctk.CTkFrame(scrollable, corner_radius=10, fg_color="#2a2a2a")
        card.grid(row=0, column=i, padx=8, pady=8, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        try:
            value = value_fn()
        except Exception:
            value = "—"
        ctk.CTkLabel(card, text=label, font=("Segoe UI", 10), text_color="#8b8c8d").pack(padx=14, pady=(10, 4))
        ctk.CTkLabel(card, text=value, font=("Segoe UI", 24, "bold"), text_color=color).pack(padx=14, pady=(0, 12))

    summary_card = ctk.CTkFrame(scrollable, corner_radius=10)
    summary_card.grid(row=1, column=0, columnspan=2, padx=8, pady=8, sticky="ew")
    summary_card.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(summary_card, text="📊 Summary", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 8))

    try:
        today_date = datetime.now().strftime('%Y-%m-%d')
        today_count = count_attendance_by_date(today_date)
        summary_text = (
            f"Today's Attendance: {today_count} students\n"
            f"Total Students: {len(get_all_students())}\n"
            f"Total Records: {len(get_attendance_all())}\n"
            f"\nSystem is {( 'Connected' if app.serial_handler.connected else 'Disconnected' )}"
        )
    except Exception as e:
        summary_text = f"Could not load statistics: {e}"

    ctk.CTkLabel(summary_card, text=summary_text, font=("Segoe UI", 11), text_color="#8b8c8d", justify="left").pack(anchor="w", padx=14, pady=(0, 12))

    report_card = ctk.CTkFrame(scrollable, corner_radius=10)
    report_card.grid(row=2, column=0, columnspan=2, padx=8, pady=8, sticky="ew")
    report_card.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(report_card, text="📄 Generate Report", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 8))
    button_row = ctk.CTkFrame(report_card, fg_color="transparent")
    button_row.pack(anchor="w", padx=14, pady=(0, 12), fill="x")

    ctk.CTkButton(
        button_row,
        text="📋 View Report",
        width=140,
        height=40,
        corner_radius=8,
        command=app.show_statistics_report,
        state="normal" if app.has_permission("export") else "disabled",
    ).pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        button_row,
        text="💾 Export Report",
        width=140,
        height=40,
        corner_radius=8,
        command=app.export_statistics_report,
        fg_color="#27ae60",
        state="normal" if app.has_permission("export") else "disabled",
    ).pack(side="left")

    if getattr(app, 'PILLOW_AVAILABLE', False):
        charts_card = ctk.CTkFrame(scrollable, corner_radius=10)
        charts_card.grid(row=3, column=0, columnspan=2, padx=8, pady=8, sticky="ew")
        charts_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(charts_card, text="📈 Visual Analytics", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 8))
        button_row = ctk.CTkFrame(charts_card, fg_color="transparent")
        button_row.pack(anchor="w", padx=14, pady=(0, 12), fill="x")
        ctk.CTkButton(
            button_row,
            text="📊 Show Charts",
            width=140,
            height=40,
            corner_radius=8,
            command=app.show_statistics_charts,
            fg_color="#9333ea",
        ).pack(side="left")
