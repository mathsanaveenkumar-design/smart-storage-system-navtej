import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from db import ensure_location, upsert_component_and_receive_stock


class AddPage(ttk.Frame):
    """
    ADD page: add new component and receive stock into a specific rack/shelf/position.
    """

    def __init__(self, master, set_status, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.set_status = set_status
        self.configure(style="Page.TFrame")

        self.photo_path = None

        self.columnconfigure(1, weight=1)

        # Vendor
        ttk.Label(self, text="Vendor Name", style="TLabel").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.vendor_entry = ttk.Entry(self, width=30)
        self.vendor_entry.grid(row=0, column=1, padx=10, pady=5, sticky="we")

        # Component name
        ttk.Label(self, text="Component Name", style="TLabel").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.comp_name_entry = ttk.Entry(self, width=30)
        self.comp_name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="we")

        # Part number / value
        ttk.Label(self, text="Part Number / Value", style="TLabel").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.part_entry = ttk.Entry(self, width=30)
        self.part_entry.grid(row=2, column=1, padx=10, pady=5, sticky="we")

        # Rack, Shelf, Position
        ttk.Label(self, text="Rack", style="TLabel").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.rack_entry = ttk.Entry(self, width=20)
        self.rack_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        ttk.Label(self, text="Shelf", style="TLabel").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.shelf_entry = ttk.Entry(self, width=20)
        self.shelf_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")

        ttk.Label(self, text="Position (optional)", style="TLabel").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.position_entry = ttk.Entry(self, width=20)
        self.position_entry.grid(row=5, column=1, padx=10, pady=5, sticky="w")

        # Quantity
        ttk.Label(self, text="Quantity", style="TLabel").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.qty_entry = ttk.Entry(self, width=10)
        self.qty_entry.grid(row=6, column=1, padx=10, pady=5, sticky="w")

        # Purpose
        ttk.Label(self, text="Purpose of Purchase", style="TLabel").grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.purpose_entry = ttk.Entry(self, width=40)
        self.purpose_entry.grid(row=7, column=1, padx=10, pady=5, sticky="we")

        # Remarks
        ttk.Label(self, text="Remarks", style="TLabel").grid(row=8, column=0, padx=10, pady=5, sticky="w")
        self.remarks_entry = ttk.Entry(self, width=40)
        self.remarks_entry.grid(row=8, column=1, padx=10, pady=5, sticky="we")

        # Photo selection
        self.photo_label = ttk.Label(self, text="No photo selected", style="TLabel")
        self.photo_label.grid(row=9, column=1, padx=10, pady=5, sticky="w")
        ttk.Button(self, text="Select Photo", command=self.select_photo).grid(row=9, column=0, padx=10, pady=5)

        # Submit button
        ttk.Button(self, text="Add / Receive", command=self.on_submit).grid(
            row=10, column=0, columnspan=2, padx=10, pady=15
        )

    def select_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if path:
            self.photo_path = path
            self.photo_label.config(text=os.path.basename(path))
            self.set_status("Photo selected (offline image sync not yet implemented).")

    def on_submit(self):
        vendor = self.vendor_entry.get().strip()
        comp_name = self.comp_name_entry.get().strip()
        part = self.part_entry.get().strip() or None
        rack = self.rack_entry.get().strip()
        shelf = self.shelf_entry.get().strip()
        position = self.position_entry.get().strip() or None
        qty_txt = self.qty_entry.get().strip()
        purpose = self.purpose_entry.get().strip()
        remarks = self.remarks_entry.get().strip()

        if not comp_name:
            messagebox.showerror("Error", "Component name is required.")
            return
        if not rack or not shelf:
            messagebox.showerror("Error", "Rack and Shelf are required.")
            return
        if not qty_txt.isdigit():
            messagebox.showerror("Error", "Quantity must be a positive integer.")
            return

        qty = int(qty_txt)
        if qty <= 0:
            messagebox.showerror("Error", "Quantity must be greater than zero.")
            return

        # Ensure location exists
        loc_id = ensure_location(rack, shelf, position)
        if loc_id is None:
            messagebox.showerror("Error", "Could not create/find location (check Supabase connection).")
            return

        # TODO: upload photo_path to Supabase Storage and store URL in components if you want
        # For now, we ignore photo_path in DB operations.

        upsert_component_and_receive_stock(
            vendor=vendor,
            comp_name=comp_name,
            part_number=part,
            qty=qty,
            purpose=purpose,
            remarks=remarks,
            location_id=loc_id,
            user_name="SYSTEM",
        )

        messagebox.showinfo("Success", "Component added and stock received (queued if offline).")
        self.clear_form()

    def clear_form(self):
        self.vendor_entry.delete(0, "end")
        self.comp_name_entry.delete(0, "end")
        self.part_entry.delete(0, "end")
        self.rack_entry.delete(0, "end")
        self.shelf_entry.delete(0, "end")
        self.position_entry.delete(0, "end")
        self.qty_entry.delete(0, "end")
        self.purpose_entry.delete(0, "end")
        self.remarks_entry.delete(0, "end")
        self.photo_path = None
        self.photo_label.config(text="No photo selected")
        self.set_status("Ready.")
