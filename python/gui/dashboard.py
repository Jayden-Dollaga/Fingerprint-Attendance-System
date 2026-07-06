import customtkinter as ctk

class DashboardPage:
    """Simple dashboard page scaffold.

    Responsibilities:
    - Build dashboard UI into a parent widget
    - Expose `refresh()` for programmatic updates
    """

    def __init__(self, app):
        self.app = app
        self.container = None

    def build(self, parent):
        self.container = ctk.CTkFrame(parent, fg_color="transparent")
        self.container.grid(sticky="nsew")
        ctk.CTkLabel(self.container, text="Dashboard", font=("Segoe UI", 14, "bold")).pack(padx=12, pady=12)
        return self.container

    def refresh(self):
        # Placeholder: update dashboard widgets when called
        pass
