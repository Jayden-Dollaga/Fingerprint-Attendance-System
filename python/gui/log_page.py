import customtkinter as ctk


def build_log_tab(app, tab):
    tab.grid_columnconfigure(0, weight=1)
    tab.grid_rowconfigure(1, weight=1)

    header_row = ctk.CTkFrame(tab, fg_color="transparent")
    header_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    header_row.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(header_row, text="Live Log", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
    ctk.CTkButton(header_row, text="Clear", width=80, command=app.clear_log,
                  fg_color="transparent", border_width=1).grid(row=0, column=1, sticky="e")

    card = ctk.CTkFrame(tab, corner_radius=10)
    card.grid(row=1, column=0, sticky="nsew")
    card.grid_columnconfigure(0, weight=1)
    card.grid_rowconfigure(0, weight=1)

    app.log_text = ctk.CTkTextbox(card, font=("Consolas", 12), wrap="word")
    app.log_text.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
    app.log_text.insert("end", "System ready.\n")
    app.log_text.configure(state="disabled")
