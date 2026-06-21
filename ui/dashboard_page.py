import tkinter as tk
from tkinter import ttk
from typing import Callable

from db import get_total_items, get_low_stock_count, get_recent_movements, pretty_name


class DashboardPage(ttk.Frame):
    def __init__(self, master, set_status: Callable[[str], None], *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.set_status = set_status

        self.configure(style="Page.TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Top cards frame
        cards_frame = ttk.Frame(self, style="Page.TFrame")
        cards_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        cards_frame.columnconfigure((0, 1, 2), weight=1)

        self.total_items_var = tk.StringVar(value="0")
        self.low_stock_var = tk.StringVar(value="0")

        total_frame = ttk.Frame(cards_frame, style="Card.TFrame", padding=10)
        total_frame.grid(row=0, column=0, padx=10, sticky="ew")
        ttk.Label(total_frame, text="Total Items", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(total_frame, textvariable=self.total_items_var, style="CardValue.TLabel").pack(anchor="w")

        low_frame = ttk.Frame(cards_frame, style="Card.TFrame", padding=10)
        low_frame.grid(row=0, column=1, padx=10, sticky="ew")
        ttk.Label(low_frame, text="Low Stock Components", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(low_frame, textvariable=self.low_stock_var, style="CardValue.TLabel").pack(anchor="w")

        # Recent activity
        recent_frame = ttk.Frame(self, style="Page.TFrame")
        recent_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        recent_frame.columnconfigure(0, weight=1)
        recent_frame.rowconfigure(1, weight=1)

        ttk.Label(recent_frame, text="Recent Activity", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        columns = ("time", "type", "component", "location", "qty", "user")
        self.tree = ttk.Treeview(recent_frame, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
        self.tree.column("time", width=150)
        self.tree.column("type", width=80)
        self.tree.column("component", width=180)
        self.tree.column("location", width=180)
        self.tree.column("qty", width=60, anchor="e")
        self.tree.column("user", width=100)

        self.tree.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(recent_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

    def refresh(self):
        # Called whenever Dashboard tab is shown
        total = get_total_items()
        self.total_items_var.set(str(total))

        low = get_low_stock_count()
        self.low_stock_var.set(str(low))

        for i in self.tree.get_children():
            self.tree.delete(i)

        movements = get_recent_movements(limit=10)
        for mv in movements:
            comp = f"{mv.get('component_id', '')}"
            loc = ""
            row = (
                mv.get("created_at", ""),
                mv.get("movement_type", ""),
                comp,
                loc,
                mv.get("quantity", 0),
                mv.get("user_name", ""),
            )
            self.tree.insert("", "end", values=row)
