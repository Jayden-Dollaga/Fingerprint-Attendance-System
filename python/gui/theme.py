import customtkinter as ctk

# Centralized theme helpers

def apply_default_theme(app):
    try:
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')
    except Exception:
        pass

def apply_light_theme(app):
    try:
        ctk.set_appearance_mode('light')
    except Exception:
        pass

def toggle_theme(app):
    try:
        current = ctk.get_appearance_mode()
        ctk.set_appearance_mode('light' if current == 'dark' else 'dark')
    except Exception:
        pass
