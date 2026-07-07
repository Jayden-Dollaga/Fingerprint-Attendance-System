import customtkinter as ctk
from tkinter import StringVar, messagebox

from core.commands import cmd_wipe
from core.database import list_backups, restore_database
from core.database import register_student


# Lightweight dialog helpers used by the app entry points.
def create_modal_dialog(parent, title, geometry):
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry(geometry)
    dialog.transient(parent)
    dialog.grab_set()
    return dialog


def ask_confirmation(parent, title, message):
    return messagebox.askyesno(title, message, parent=parent)


def open_enroll_dialog(app):
    if getattr(app, "enroll_dialog", None) is not None and app.enroll_dialog.winfo_exists():
        app.enroll_dialog.lift()
        app.enroll_dialog.focus()
        return app.enroll_dialog

    dialog = create_modal_dialog(app, "Enroll Fingerprint", "760x520")
    app.enroll_dialog = dialog
    app.enroll_ready_to_save = False
    app.enroll_completed = False

    app.enroll_id_var = StringVar(value="Pending")
    app.enroll_status_var = StringVar(value="Waiting for the sensor to capture a fingerprint.")

    content = ctk.CTkFrame(dialog, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=18, pady=18)

    ctk.CTkLabel(content, text="Enroll a new fingerprint", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 8))
    ctk.CTkLabel(content, text="The ESP32 will capture the fingerprint and report the assigned ID.").pack(anchor="w", pady=(0, 12))

    body = ctk.CTkFrame(content, fg_color="transparent")
    body.pack(fill="both", expand=True, pady=(0, 10))
    body.grid_columnconfigure(0, weight=1)
    body.grid_columnconfigure(1, weight=1)

    fields = ctk.CTkFrame(body, fg_color="transparent")
    fields.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    fields.grid_columnconfigure(0, weight=1)

    app.enroll_student_no_var = StringVar(value="")
    app.enroll_student_name_var = StringVar(value="")
    app.enroll_grade_var = StringVar(value="")
    app.enroll_section_var = StringVar(value="")

    for row, (label, var) in enumerate([
        ("Student No", app.enroll_student_no_var),
        ("Student Name", app.enroll_student_name_var),
        ("Grade", app.enroll_grade_var),
        ("Section", app.enroll_section_var),
    ], start=0):
        ctk.CTkLabel(fields, text=label).grid(row=row * 2, column=0, sticky="w", pady=(0, 4))
        ctk.CTkEntry(fields, textvariable=var).grid(row=row * 2 + 1, column=0, sticky="ew", pady=(0, 10))

    log_panel = ctk.CTkFrame(body, corner_radius=10)
    log_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
    log_panel.grid_rowconfigure(1, weight=1)
    log_panel.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(log_panel, text="Enrollment Log", font=("Segoe UI", 13, "bold")).grid(
        row=0, column=0, sticky="w", padx=12, pady=(12, 8)
    )
    app.enroll_log_text = ctk.CTkTextbox(log_panel, wrap="char", state="disabled")
    app.enroll_log_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    status_row = ctk.CTkFrame(content, fg_color="transparent")
    status_row.pack(fill="x", pady=(0, 8))
    ctk.CTkLabel(status_row, textvariable=app.enroll_id_var).pack(anchor="w")
    ctk.CTkLabel(status_row, textvariable=app.enroll_status_var, wraplength=340).pack(anchor="w", pady=(4, 0))

    bottom = ctk.CTkFrame(content, fg_color="transparent")
    bottom.pack(fill="x", pady=(8, 0))

    app.enroll_save_button = ctk.CTkButton(
        bottom,
        text="Save Student",
        command=lambda: save_enroll_profile(app),
        state="disabled",
        height=40,
        corner_radius=8,
    )
    app.enroll_save_button.pack(side="left")

    ctk.CTkButton(
        bottom,
        text="Cancel",
        command=lambda: close_enroll_dialog(app),
        fg_color="transparent",
        border_width=1,
        height=40,
        corner_radius=8,
    ).pack(side="right")
    dialog.protocol("WM_DELETE_WINDOW", lambda: close_enroll_dialog(app))
    return dialog


def save_enroll_profile(app):
    if not getattr(app, "enroll_dialog", None) or not app.enroll_dialog.winfo_exists():
        return False

    fingerprint_id = app.enroll_id_var.get().strip()
    if not fingerprint_id or not fingerprint_id.isdigit() or int(fingerprint_id) <= 0:
        messagebox.showwarning("Missing fingerprint", "The fingerprint has not been enrolled yet. Please wait for the sensor to confirm the ID.", parent=app)
        return False

    student_no = getattr(app, "enroll_student_no_var", None).get().strip() if getattr(app, "enroll_student_no_var", None) else ""
    student_name = getattr(app, "enroll_student_name_var", None).get().strip() if getattr(app, "enroll_student_name_var", None) else ""
    grade = getattr(app, "enroll_grade_var", None).get().strip() if getattr(app, "enroll_grade_var", None) else ""
    section = getattr(app, "enroll_section_var", None).get().strip() if getattr(app, "enroll_section_var", None) else ""

    if not all([student_no, student_name, grade, section]):
        messagebox.showwarning("Incomplete details", "Please fill in student number, name, grade, and section before saving.", parent=app)
        return False

    ok, msg = register_student(int(fingerprint_id), student_no, student_name, grade, section)
    if ok:
        app.log_message(f"Saved student profile for fingerprint ID {fingerprint_id}.")
        close_enroll_dialog(app)
        return True

    messagebox.showerror("Save failed", msg, parent=app)
    return False


def close_enroll_dialog(app):
    if getattr(app, "enroll_dialog", None) is not None and app.enroll_dialog.winfo_exists():
        app.enroll_dialog.destroy()
    app.enroll_dialog = None
    app.enroll_save_button = None
    app.enroll_ready_to_save = False
    app.enroll_completed = False
    return True


def open_wipe_dialog(app):
    if getattr(app, "wipe_dialog", None) is not None and app.wipe_dialog.winfo_exists():
        app.wipe_dialog.lift()
        app.wipe_dialog.focus()
        return app.wipe_dialog

    dialog = create_modal_dialog(app, "Confirm Wipe", "560x360")
    app.wipe_dialog = dialog
    app.wipe_status_var = StringVar(value="This will erase stored fingerprints and clear related database records.")
    app.wipe_log_text = None

    content = ctk.CTkFrame(dialog, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=18, pady=18)

    ctk.CTkLabel(content, text="Wipe fingerprints", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 8))
    ctk.CTkLabel(content, text="This action removes the stored fingerprints from the ESP32 and clears the linked student and attendance data from the local database.", wraplength=500).pack(anchor="w", pady=(0, 12))

    status_label = ctk.CTkLabel(content, textvariable=app.wipe_status_var, wraplength=500)
    status_label.pack(anchor="w", pady=(0, 10))

    button_row = ctk.CTkFrame(content, fg_color="transparent")
    button_row.pack(fill="x", pady=(8, 0))
    button_row.grid_columnconfigure(0, weight=1)
    button_row.grid_columnconfigure(1, weight=1)

    app.wipe_confirm_button = ctk.CTkButton(
        button_row,
        text="Confirm Wipe",
        command=lambda: confirm_wipe(app),
        fg_color="#e74c3c",
        hover_color="#c0392b",
        height=40,
        corner_radius=8,
        font=("Segoe UI", 12, "bold"),
    )
    app.wipe_confirm_button.grid(row=0, column=0, sticky="w")

    ctk.CTkButton(
        button_row,
        text="Cancel",
        command=lambda: close_wipe_dialog(app),
        fg_color="transparent",
        border_width=1,
        height=40,
        corner_radius=8,
        font=("Segoe UI", 12),
    ).grid(row=0, column=1, sticky="e")

    dialog.protocol("WM_DELETE_WINDOW", lambda: close_wipe_dialog(app))
    app.log_message("Opened wipe confirmation dialog.")
    return dialog


def confirm_wipe(app):
    if not getattr(app, "serial_handler", None) or not app.serial_handler.connected:
        app.log_message("Wipe skipped because the ESP32 is not connected.")
        if getattr(app, "wipe_status_var", None) is not None:
            app.wipe_status_var.set("Connect to the ESP32 before wiping.")
        return False

    if getattr(app, "wipe_confirm_button", None) is not None:
        app.wipe_confirm_button.configure(state="disabled")

    if getattr(app, "wipe_status_var", None) is not None:
        app.wipe_status_var.set("Sending wipe command to the ESP32. Please wait for confirmation.")

    app.log_message("Sent WIPE command to ESP32. Waiting for confirmation...")
    success = cmd_wipe(app.serial_handler)
    if success:
        if getattr(app, "wipe_status_var", None) is not None:
            app.wipe_status_var.set("Wipe command sent. Waiting for the ESP32 to confirm completion.")
        return True

    if getattr(app, "wipe_confirm_button", None) is not None:
        app.wipe_confirm_button.configure(state="normal")
    if getattr(app, "wipe_status_var", None) is not None:
        app.wipe_status_var.set("Failed to send the wipe command. Check the serial connection and try again.")
    app.log_message("Failed to send WIPE command to ESP32.")
    return False


def close_wipe_dialog(app):
    if getattr(app, "wipe_dialog", None) is not None and app.wipe_dialog.winfo_exists():
        app.wipe_dialog.destroy()
    app.wipe_dialog = None
    app.wipe_confirm_button = None
    app.wipe_status_var = None
    app.wipe_log_text = None
    return True


def open_restore_dialog(app):
    backups = list_backups()
    if not backups:
        messagebox.showinfo("No backups", "No database backups are available yet.", parent=app)
        return None

    backup_name = backups[0]["name"]
    if not ask_confirmation(app, "Restore Database", f"Restore from {backup_name} and replace the current database?"):
        return False

    success, message = restore_database(backups[0]["path"])
    if success:
        app.log_message(f"Restored database from {backup_name}.")
        app.refresh_attendance_view()
        app.refresh_student_list()
        app.refresh_statistics()
        messagebox.showinfo("Restore Complete", message, parent=app)
        return True

    app.log_message(f"Restore failed: {message}")
    messagebox.showerror("Restore Failed", message, parent=app)
    return False
