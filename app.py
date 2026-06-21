import threading
import tkinter as tk
from tkinter import ttk

from db import background_sync_loop, init_supabase, online_flag, offline_queue
from ui.dashboard_page import DashboardPage
from ui.add_page import AddPage


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Smart Storage Management System")
        self.geometry("1100x650")

        style = ttk.Style(self)
        style.theme_use("clam")

        # Global styles
        style.configure("Sidebar.TFrame", background="black")
        style.configure("Sidebar.TLabel", background="black", foreground="white", font=("Arial", 14, "bold"))
        style.configure("SidebarButton.TButton", background="white", foreground="black")
        style.map("SidebarButton.TButton", background=[("active", "#cccccc")])

        style.configure("Page.TFrame", background="black")
        style.configure("TLabel", background="black", foreground="white")

        style.configure("Card.TFrame", background="black", relief="ridge")
        style.configure("CardTitle.TLabel", background="black", foreground="white", font=("Arial", 10, "bold"))
        style.configure("CardValue.TLabel", background="black", foreground="white", font=("Arial", 18, "bold"))

        style.configure("SectionTitle.TLabel", background="black", foreground="white", font=("Arial", 12, "bold"))

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=200)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        ttk.Label(self.sidebar, text="Smart Storage", style="Sidebar.TLabel").pack(padx=20, pady=20)

        self.btn_dashboard = ttk.Button(self.sidebar, text="Dashboard", style="SidebarButton.TButton",
                                        command=self.show_dashboard)
        self.btn_dashboard.pack(padx=10, pady=5, fill="x")

        # Placeholders for other tabs (to be implemented later)
        self.btn_add = ttk.Button(self.sidebar, text="Add", style="SidebarButton.TButton",
                          command=self.show_add)
        self.btn_add.pack(padx=10, pady=5, fill="x")
        self.btn_manage = ttk.Button(self.sidebar, text="Manage", style="SidebarButton.TButton",
                                     command=self.show_dashboard)
        self.btn_manage.pack(padx=10, pady=5, fill="x")
        self.btn_use = ttk.Button(self.sidebar, text="Use", style="SidebarButton.TButton",
                                  command=self.show_dashboard)
        self.btn_use.pack(padx=10, pady=5, fill="x")
        self.btn_history = ttk.Button(self.sidebar, text="History", style="SidebarButton.TButton",
                                      command=self.show_dashboard)
        self.btn_history.pack(padx=10, pady=5, fill="x")
        self.btn_adjust = ttk.Button(self.sidebar, text="Adjust", style="SidebarButton.TButton",
                                     command=self.show_dashboard)
        self.btn_adjust.pack(padx=10, pady=5, fill="x")

        self.status_var = tk.StringVar(value="Checking connection...")
        ttk.Label(self.sidebar, textvariable=self.status_var, style="Sidebar.TLabel").pack(
            side="bottom", padx=10, pady=10
        )

        # Main container
        self.container = ttk.Frame(self, style="Page.TFrame")
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(0, weight=1)

        # Pages
        self.dashboard_page = DashboardPage(self.container, self.set_status)
        self.dashboard_page.grid(row=0, column=0, sticky="nsew")

        self.add_page = AddPage(self.container, self.set_status)
        self.add_page.grid(row=0, column=0, sticky="nsew")

        # Later: AddPage, ManagePage, UsePage, HistoryPage, AdjustPage instances

        self.show_dashboard()
        self.after(1000, self.update_status)

    def set_status(self, text: str):
        self.status_var.set(text)

    def show_dashboard(self):
        self.dashboard_page.refresh()
        self.dashboard_page.tkraise()

    def update_status(self):
        if online_flag:
            self.status_var.set(f"Online (Queued: {len(offline_queue)})")
        else:
            self.status_var.set(f"Offline (Queued: {len(offline_queue)})")
        self.after(2000, self.update_status)
    
    def show_add(self):
        self.add_page.tkraise()
        self.set_status("Add / Receive components.")

if __name__ == "__main__":
    threading.Thread(target=background_sync_loop, daemon=True).start()
    init_supabase()
    app = App()
    app.mainloop()
