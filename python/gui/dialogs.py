import customtkinter as ctk
from tkinter import messagebox


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
    return None


def save_enroll_profile(app):
    return None


def close_enroll_dialog(app):
    return None


def open_wipe_dialog(app):
    return None


def confirm_wipe(app):
    return None


def close_wipe_dialog(app):
    return None


def open_restore_dialog(app):
    return None
