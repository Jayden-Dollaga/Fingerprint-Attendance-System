import customtkinter as ctk
from tkinter import messagebox

from core.commands import cmd_stop, cmd_delete
from services.student_service import StudentService


class StudentsPage:
    def __init__(self, app):
        self.app = app
        self.service = StudentService()
        self.dialog = None
        self.list_frame = None

    def open_list_dialog(self):
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.lift()
            self.dialog.focus()
            self.refresh()
            return

        dialog = ctk.CTkToplevel(self.app)
        dialog.title("Registered Students")
        dialog.geometry("380x520")
        dialog.transient(self.app)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(dialog, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Registered Students", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            header,
            text="↻",
            width=28,
            height=26,
            fg_color="transparent",
            border_width=1,
            command=self.refresh,
        ).grid(row=0, column=1, sticky="e")

        self.list_frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        self.list_frame.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            dialog,
            text="Close",
            command=self.close_dialog,
            fg_color="transparent",
            border_width=1,
        ).grid(row=2, column=0, padx=16, pady=(0, 16), sticky="ew")

        dialog.protocol("WM_DELETE_WINDOW", self.close_dialog)
        self.dialog = dialog
        self.refresh()

    def close_dialog(self):
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.grab_release()
            self.dialog.destroy()
        self.dialog = None
        self.list_frame = None

    def refresh(self):
        if self.list_frame is None or not self.list_frame.winfo_exists():
            return

        for child in self.list_frame.winfo_children():
            child.destroy()

        students = self.service.get_all_students()
        if not students:
            ctk.CTkLabel(
                self.list_frame,
                text="No students yet.",
                text_color="#8b8b8d",
                font=("Segoe UI", 11),
            ).pack(anchor="w", padx=4, pady=8)
            return

        for student in students:
            self._build_student_row(student).pack(fill="x", padx=2, pady=4)

    def _build_student_row(self, student):
        fingerprint_id = student["fingerprint_id"]

        row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        row.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(info, text=student["student_name"], font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            info,
            text=f"ID {fingerprint_id}  ·  No. {student['student_no']}",
            font=("Segoe UI", 10),
            text_color="#8b8b8d",
        ).pack(anchor="w")

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.grid(row=0, column=1, padx=(4, 0), sticky="e")

        ctk.CTkButton(
            actions,
            text="✎",
            width=28,
            height=24,
            fg_color="transparent",
            border_width=1,
            command=lambda fid=fingerprint_id: self.open_edit_dialog(fid),
            state="normal" if self.app.has_permission("enroll") else "disabled",
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            actions,
            text="🗑",
            width=28,
            height=24,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=lambda fid=fingerprint_id: self.delete_student(fid),
            state="normal" if self.app.has_permission("delete") else "disabled",
        ).pack(side="left")

        return row

    def delete_student(self, fingerprint_id, parent=None):
        if parent is None:
            parent = self.dialog if self.dialog is not None and self.dialog.winfo_exists() else self.app

        if not self.app.has_permission("delete"):
            messagebox.showerror(
                "Permission Denied",
                "Your role does not have permission to delete students.",
                parent=parent,
            )
            return False

        if self.app.serial_handler.connected:
            if hasattr(self.app, "enroll_dialog") and self.app.enroll_dialog is not None and self.app.enroll_dialog.winfo_exists():
                messagebox.showwarning(
                    "Delete Disabled",
                    "An enrollment is currently active. Close or cancel enrollment before deleting a fingerprint.",
                    parent=parent,
                )
                return False

            if hasattr(self.app, "stop_button") and self.app.stop_button.cget("state") == "normal":
                if messagebox.askyesno(
                    "Stop Scan First",
                    "The ESP32 is currently scanning. Stop scanning before deleting this fingerprint?",
                    parent=parent,
                ):
                    if cmd_stop(self.app.serial_handler):
                        self.app.stop_button.configure(state="disabled")
                        self.app.log_message("Sent STOP command to ESP32 before deleting fingerprint.")
                    else:
                        messagebox.showerror(
                            "Delete Error",
                            "Could not stop scan mode on the ESP32. Try again.",
                            parent=parent,
                        )
                        return False
                else:
                    return False

        if self.app.serial_handler.connected:
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

        if self.app.serial_handler.connected:
            if not cmd_delete(self.app.serial_handler, fingerprint_id):
                messagebox.showerror(
                    "Delete Error",
                    f"Could not send DELETE:{fingerprint_id} to ESP32.",
                    parent=parent,
                )
                return False
            self.app.log_message(f"Sent DELETE:{fingerprint_id} command to ESP32.")

        self.service.delete_student(fingerprint_id)
        self.refresh()
        self.app.refresh_statistics()
        self.app.log_message(f"Deleted student profile for ID {fingerprint_id}.")
        return True

    def open_edit_dialog(self, fingerprint_id):
        student = self.service.get_student(fingerprint_id)
        if not student:
            return

        dialog = ctk.CTkToplevel(self.app)
        dialog.title(f"Edit Student — ID {fingerprint_id}")
        dialog.geometry("340x460")
        dialog.transient(self.app)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        form = ctk.CTkFrame(dialog, corner_radius=10)
        form.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Student Profile", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, padx=14, pady=(14, 10), sticky="w"
        )

        id_var = ctk.StringVar(value=str(fingerprint_id))
        no_var = ctk.StringVar(value=student["student_no"])
        name_var = ctk.StringVar(value=student["student_name"])
        grade_var = ctk.StringVar(value=student["grade"])
        section_var = ctk.StringVar(value=student["section"])
        status_var = ctk.StringVar(value="")

        ctk.CTkLabel(form, text="Fingerprint ID", font=("Segoe UI", 11), text_color="#8b8b8d").grid(
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
            ctk.CTkLabel(form, text=label, font=("Segoe UI", 11), text_color="#8b8b8d").grid(
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
            ok, msg = self.service.save_student(fingerprint_id, student_no, student_name, grade, section)
            if ok:
                status_var.set("Saved.")
                self.refresh()
                self.app.refresh_statistics()
                self.app.log_message(f"Student profile updated: ID {fingerprint_id} - {student_name}")
                dialog.after(400, dialog.destroy)
            else:
                status_var.set(msg)

        def do_delete():
            if self.delete_student(fingerprint_id, parent=dialog):
                dialog.destroy()

        button_row = ctk.CTkFrame(form, fg_color="transparent")
        button_row.grid(row=row, column=0, padx=14, pady=(8, 6), sticky="ew")
        button_row.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(
            button_row,
            text="Save",
            command=do_save,
            height=40,
            corner_radius=8,
            state="normal" if self.app.has_permission("enroll") else "disabled",
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(
            button_row,
            text="Delete",
            command=do_delete,
            height=40,
            corner_radius=8,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            state="normal" if self.app.has_permission("delete") else "disabled",
        ).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(
            button_row,
            text="Close",
            command=dialog.destroy,
            height=40,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
        ).grid(row=0, column=2, padx=(4, 0), sticky="ew")

        ctk.CTkLabel(
            form,
            textvariable=status_var,
            text_color="#8b8b8d",
            wraplength=260,
            justify="left",
        ).grid(row=row + 1, column=0, padx=14, pady=(4, 14), sticky="w")

    def open_add_student_dialog(self, fingerprint_id: int):
        if fingerprint_id is None or int(fingerprint_id) <= 0:
            messagebox.showerror(
                "Invalid Fingerprint ID",
                "Only real fingerprint IDs can be registered as students.",
                parent=self.app,
            )
            return

        dialog = ctk.CTkToplevel(self.app)
        dialog.title(f"Add Student — ID {fingerprint_id}")
        dialog.geometry("340x460")
        dialog.transient(self.app)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        form = ctk.CTkFrame(dialog, corner_radius=10)
        form.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Student Profile", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, padx=14, pady=(14, 10), sticky="w"
        )

        id_var = ctk.StringVar(value=str(fingerprint_id))
        no_var = ctk.StringVar(value="")
        name_var = ctk.StringVar(value="")
        grade_var = ctk.StringVar(value="")
        section_var = ctk.StringVar(value="")
        status_var = ctk.StringVar(value="")

        ctk.CTkLabel(form, text="Fingerprint ID", font=("Segoe UI", 11), text_color="#8b8b8d").grid(
            row=1, column=0, padx=14, pady=(6, 0), sticky="w"
        )
        ctk.CTkEntry(form, textvariable=id_var, state="disabled").grid(
            row=2, column=0, padx=14, pady=(2, 6), sticky="ew"
        )

        fields = [
            ("Student No.", no_var, f"Leave blank to use ID{fingerprint_id}"),
            ("Name", name_var, "Full name"),
            ("Grade", grade_var, "e.g. 10"),
            ("Section", section_var, "e.g. Diamond"),
        ]
        row = 3
        for label, var, placeholder in fields:
            ctk.CTkLabel(form, text=label, font=("Segoe UI", 11), text_color="#8b8b8d").grid(
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
            ok, msg = self.service.save_student(fingerprint_id, student_no, student_name, grade, section)
            if ok:
                status_var.set("Saved.")
                self.refresh()
                self.app.refresh_statistics()
                self.app.log_message(f"Student profile created: ID {fingerprint_id} - {student_name}")
                dialog.after(400, dialog.destroy)
                self.app.refresh_attendance_view()
            else:
                status_var.set(msg)

        button_row = ctk.CTkFrame(form, fg_color="transparent")
        button_row.grid(row=row, column=0, padx=14, pady=(8, 6), sticky="ew")
        button_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            button_row,
            text="Save",
            command=do_save,
            height=40,
            corner_radius=8,
            state="normal" if self.app.has_permission("enroll") else "disabled",
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(
            button_row,
            text="Close",
            command=dialog.destroy,
            height=40,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        ctk.CTkLabel(
            form,
            textvariable=status_var,
            text_color="#8b8b8d",
            wraplength=260,
            justify="left",
        ).grid(row=row + 1, column=0, padx=14, pady=(4, 14), sticky="w")


def _get_page(app):
    page = getattr(app, 'students_page', None)
    if page is None:
        page = StudentsPage(app)
        app.students_page = page
    return page


def open_students_list_dialog(app):
    return _get_page(app).open_list_dialog()


def close_students_dialog(app):
    return _get_page(app).close_dialog()


def refresh_student_list(app):
    return _get_page(app).refresh()


def delete_student_from_list(app, fingerprint_id, parent=None):
    return _get_page(app).delete_student(fingerprint_id, parent=parent)


def open_edit_dialog(app, fingerprint_id):
    return _get_page(app).open_edit_dialog(fingerprint_id)


def open_add_student_dialog(app, fingerprint_id: int):
    return _get_page(app).open_add_student_dialog(fingerprint_id)
