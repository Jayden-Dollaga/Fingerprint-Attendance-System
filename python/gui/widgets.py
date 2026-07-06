import customtkinter as ctk


def section_header(parent, title, font=None, text_color="#f8fafc"):
    if font is None:
        font = ("Segoe UI", 13, "bold")
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(frame, text=title, font=font, text_color=text_color).grid(row=0, column=0, sticky="w")
    return frame


def card_frame(parent, corner_radius=10, fg_color=None):
    return ctk.CTkFrame(parent, corner_radius=corner_radius, fg_color=fg_color)


def action_button(parent, **kwargs):
    return ctk.CTkButton(parent, **kwargs)


def subtle_label(parent, text, font=None):
    if font is None:
        font = ("Segoe UI", 11)
    return ctk.CTkLabel(parent, text=text, font=font, text_color="#8b8b8d")
