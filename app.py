import os
import datetime
import threading
import time
from typing import List, Dict, Any, Optional

import customtkinter as ctk
from supabase import create_client, Client
from dotenv import load_dotenv
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

# ---------- Config & Supabase client ----------

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
EMPLOYEES = [u.strip() for u in os.getenv("EMPLOYEES", "User1,User2").split(",") if u.strip()]

supabase: Optional[Client] = None
offline_queue: List[Dict[str, Any]] = []
online_flag = False


def normalize_key(text: str) -> str:
    return text.strip().upper().replace(" ", "_")


def pretty_name(text: Optional[str]) -> str:
    if not text:
        return ""
    t = text.replace("_", " ").lower().strip()
    return " ".join([w.capitalize() for w in t.split()])


def now_ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def init_supabase():
    global supabase, online_flag
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase.table("components").select("id").limit(1).execute()
        online_flag = True
    except Exception:
        supabase = None
        online_flag = False


def queue_or_run(table: str, data: Dict[str, Any], op_type: str = "insert", row_id: Optional[int] = None):
    global supabase, offline_queue
    if supabase is None:
        offline_queue.append({"type": op_type, "table": table, "data": data, "id": row_id})
        return
    try:
        if op_type == "insert":
            supabase.table(table).insert(data).execute()
        elif op_type == "update":
            supabase.table(table).update(data).eq("id", row_id).execute()
    except Exception:
        offline_queue.append({"type": op_type, "table": table, "data": data, "id": row_id})


def background_sync():
    global online_flag, supabase, offline_queue
    while True:
        if supabase is None:
            init_supabase()
        if supabase is not None:
            try:
                while offline_queue:
                    op = offline_queue.pop(0)
                    if op["type"] == "insert":
                        supabase.table(op["table"]).insert(op["data"]).execute()
                    elif op["type"] == "update":
                        supabase.table(op["table"]).update(op["data"]).eq("id", op["id"]).execute()
                online_flag = True
            except Exception:
                online_flag = False
        time.sleep(5)


# ---------- GUI Pages ----------

class AddPage(ctk.CTkFrame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.photo_path = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        # Vendor
        ctk.CTkLabel(self, text="Vendor Name").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.vendor_entry = ctk.CTkEntry(self, width=250)
        self.vendor_entry.grid(row=0, column=1, padx=10, pady=5, sticky="we")

        # Component Name
        ctk.CTkLabel(self, text="Component Name").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.comp_name_entry = ctk.CTkEntry(self, width=250)
        self.comp_name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="we")
        self.comp_name_entry.bind("<KeyRelease>", self.update_suggestions)

        self.suggestions_combo = ctk.CTkComboBox(self, values=[], width=200)
        self.suggestions_combo.grid(row=1, column=2, padx=10, pady=5, sticky="we")

        # Part Number
        ctk.CTkLabel(self, text="Part Number / Value").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.part_entry = ctk.CTkEntry(self, width=250)
        self.part_entry.grid(row=2, column=1, padx=10, pady=5, sticky="we")

        # Location
        ctk.CTkLabel(self, text="Location (Rack/Shelf)").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.location_combo = ctk.CTkComboBox(self, values=[], width=250)
        self.location_combo.grid(row=3, column=1, padx=10, pady=5, sticky="we")

        # Quantity
        ctk.CTkLabel(self, text="Quantity").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.qty_entry = ctk.CTkEntry(self, width=100)
        self.qty_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")

        # Purpose
        ctk.CTkLabel(self, text="Purpose of Purchase").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.purpose_entry = ctk.CTkEntry(self, width=350)
        self.purpose_entry.grid(row=5, column=1, padx=10, pady=5, sticky="we")

        # Remarks
        ctk.CTkLabel(self, text="Remarks").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.remarks_entry = ctk.CTkEntry(self, width=350)
        self.remarks_entry.grid(row=6, column=1, padx=10, pady=5, sticky="we")

        # Photo
        ctk.CTkButton(self, text="Select Photo", command=self.select_photo).grid(row=7, column=0, padx=10, pady=5)
        self.photo_label = ctk.CTkLabel(self, text="No photo selected")
        self.photo_label.grid(row=7, column=1, padx=10, pady=5, sticky="w")

        # Submit
        self.add_button = ctk.CTkButton(self, text="Add / Update + Receive", command=self.add_component)
        self.add_button.grid(row=8, column=0, columnspan=2, padx=10, pady=20)

        self.refresh_locations()

    def select_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if path:
            self.photo_path = path
            self.photo_label.configure(text=os.path.basename(path))

    def refresh_locations(self):
        if supabase is None:
            return
        try:
            res = supabase.table("locations").select("*").order("display_name").execute()
            self.locations = res.data
            names = [loc["display_name"] for loc in self.locations]
            self.location_combo.configure(values=names)
            if names:
                self.location_combo.set(names[0])
        except Exception:
            self.locations = []
            self.location_combo.configure(values=[])

    def get_selected_location_id(self) -> Optional[int]:
        if not hasattr(self, "locations"):
            return None
        current = self.location_combo.get()
        for loc in self.locations:
            if loc["display_name"] == current:
                return loc["id"]
        return None

    def update_suggestions(self, event=None):
        if supabase is None:
            return
        term = normalize_key(self.comp_name_entry.get())
        if not term:
            self.suggestions_combo.configure(values=[])
            return
        try:
            res = supabase.table("components").select("component_name_raw").ilike("component_name_raw", f"%{term}%").limit(5).execute()
            names = list({row["component_name_raw"] for row in res.data})
            self.suggestions_combo.configure(values=names)
        except Exception:
            pass

    def add_component(self):
        vendor = self.vendor_entry.get().strip()
        cname_raw = normalize_key(self.comp_name_entry.get())
        part_raw = normalize_key(self.part_entry.get()) if self.part_entry.get().strip() else None
        qty_txt = self.qty_entry.get().strip()
        purpose = self.purpose_entry.get().strip()
        remarks = self.remarks_entry.get().strip()
        loc_id = self.get_selected_location_id()

        if not cname_raw or not qty_txt.isdigit() or loc_id is None:
            messagebox.showerror("Error", "Component name, valid quantity, and location are required.")
            return

        qty = int(qty_txt)
        comp_key = cname_raw + "_" + (part_raw if part_raw else "NO_PART")
        ts = now_ts()
        photo_url = None

        comp_id = None
        if supabase is not None:
            try:
                res = supabase.table("components").select("*").eq("component_key", comp_key).execute()
                if res.data:
                    comp = res.data[0]
                    comp_id = comp["id"]
                    update_data = {
                        "vendor_name": vendor,
                        "purpose_of_purchase": purpose,
                        "remarks": remarks,
                        "updated_at": ts
                    }
                    queue_or_run("components", update_data, "update", comp_id)
                else:
                    insert_data = {
                        "component_key": comp_key,
                        "component_name_raw": cname_raw,
                        "part_number_raw": part_raw,
                        "vendor_name": vendor,
                        "photo_url": photo_url,
                        "purpose_of_purchase": purpose,
                        "remarks": remarks,
                        "created_at": ts,
                        "updated_at": ts
                    }
                    queue_or_run("components", insert_data, "insert")
                    res2 = supabase.table("components").select("id").eq("component_key", comp_key).single().execute()
                    comp_id = res2.data["id"]
            except Exception:
                pass

        if comp_id is None:
            messagebox.showwarning("Info", "Component queued. Stocks will be updated when online.")
            return

        # UPSERT into stocks (component_id, location_id)
        if supabase is not None:
            try:
                res = supabase.table("stocks").select("*").eq("component_id", comp_id).eq("location_id", loc_id).execute()
                if res.data:
                    row = res.data[0]
                    new_qty = (row["quantity"] or 0) + qty
                    queue_or_run("stocks", {"quantity": new_qty, "updated_at": ts}, "update", row["id"])
                else:
                    queue_or_run("stocks", {"component_id": comp_id, "location_id": loc_id, "quantity": qty, "updated_at": ts}, "insert")
            except Exception:
                pass
        else:
            queue_or_run("stocks", {"component_id": comp_id, "location_id": loc_id, "quantity": qty, "updated_at": ts}, "insert")

        # Add stock_movements
        data_mv = {
            "component_id": comp_id,
            "from_location_id": None,
            "to_location_id": loc_id,
            "quantity": qty,
            "movement_type": "ADD",
            "user_name": "SYSTEM",
            "purpose": purpose,
            "remarks": remarks,
            "movement_date": datetime.date.today().isoformat(),
            "created_at": ts
        }
        queue_or_run("stock_movements", data_mv, "insert")

        messagebox.showinfo("Done", "Component added/received (queued if offline).")
        self.clear_form()

    def clear_form(self):
        self.vendor_entry.delete(0, "end")
        self.comp_name_entry.delete(0, "end")
        self.part_entry.delete(0, "end")
        self.qty_entry.delete(0, "end")
        self.purpose_entry.delete(0, "end")
        self.remarks_entry.delete(0, "end")
        self.photo_path = None
        self.photo_label.configure(text="No photo selected")


class ManagePage(ctk.CTkFrame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.locations = []
        self.selected_location_id = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self, text="New Location (Rack/Shelf)").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.location_entry = ctk.CTkEntry(self, width=250)
        self.location_entry.grid(row=0, column=1, padx=10, pady=5, sticky="we")
        ctk.CTkButton(self, text="Add Location", command=self.add_location).grid(row=0, column=2, padx=10, pady=5)

        ctk.CTkLabel(self, text="Select Location").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.location_combo = ctk.CTkComboBox(self, values=[], command=self.on_location_change)
        self.location_combo.grid(row=1, column=1, padx=10, pady=5, sticky="we")

        ctk.CTkLabel(self, text="Search Component").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.search_entry = ctk.CTkEntry(self, width=250)
        self.search_entry.grid(row=2, column=1, padx=10, pady=5, sticky="we")
        self.search_entry.bind("<KeyRelease>", self.refresh_components)

        self.tree = ttk.Treeview(self, columns=("name", "part", "qty"), show="headings")
        self.tree.heading("name", text="Component")
        self.tree.heading("part", text="Part Number / Value")
        self.tree.heading("qty", text="Qty at Location")
        self.tree.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        self.refresh_locations()

    def add_location(self):
        name_raw = self.location_entry.get().strip()
        if not name_raw:
            return
        loc_key = normalize_key(name_raw)
        display = pretty_name(loc_key)
        ts = now_ts()
        data = {"location_key": loc_key, "display_name": display, "created_at": ts}
        queue_or_run("locations", data, "insert")
        self.location_entry.delete(0, "end")
        self.refresh_locations()

    def refresh_locations(self):
        if supabase is None:
            return
        try:
            res = supabase.table("locations").select("*").order("display_name").execute()
            self.locations = res.data
            names = [loc["display_name"] for loc in self.locations]
            self.location_combo.configure(values=names)
            if names:
                self.location_combo.set(names[0])
                self.selected_location_id = self.locations[0]["id"]
                self.refresh_components()
        except Exception:
            pass

    def on_location_change(self, value: str):
        for loc in self.locations:
            if loc["display_name"] == value:
                self.selected_location_id = loc["id"]
                break
        self.refresh_components()

    def refresh_components(self, event=None):
        if supabase is None or self.selected_location_id is None:
            return
        term = self.search_entry.get().strip().lower()
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            res = supabase.table("stocks").select(
                "id, quantity, components(id, component_name_raw, part_number_raw)"
            ).eq("location_id", self.selected_location_id).execute()
            for row in res.data:
                comp = row["components"]
                name_pretty = pretty_name(comp["component_name_raw"])
                part_pretty = pretty_name(comp["part_number_raw"])
                if term and term not in name_pretty.lower() and term not in part_pretty.lower():
                    continue
                self.tree.insert("", "end", values=(name_pretty, part_pretty, row["quantity"]))
        except Exception:
            pass


class UsePage(ctk.CTkFrame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.components_cache = []
        self.locations = []

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="User").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.user_combo = ctk.CTkComboBox(self, values=EMPLOYEES)
        self.user_combo.grid(row=0, column=1, padx=10, pady=5, sticky="we")

        ctk.CTkLabel(self, text="Location").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.location_combo = ctk.CTkComboBox(self, values=[], command=self.update_components)
        self.location_combo.grid(row=1, column=1, padx=10, pady=5, sticky="we")

        ctk.CTkLabel(self, text="Search Component").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.search_entry = ctk.CTkEntry(self, width=250)
        self.search_entry.grid(row=2, column=1, padx=10, pady=5, sticky="we")
        self.search_entry.bind("<KeyRelease>", self.update_components)

        ctk.CTkLabel(self, text="Component").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.comp_combo = ctk.CTkComboBox(self, values=[])
        self.comp_combo.grid(row=3, column=1, padx=10, pady=5, sticky="we")

        ctk.CTkLabel(self, text="Quantity").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.qty_entry = ctk.CTkEntry(self, width=100)
        self.qty_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self, text="Purpose").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.purpose_entry = ctk.CTkEntry(self, width=350)
        self.purpose_entry.grid(row=5, column=1, padx=10, pady=5, sticky="we")

        ctk.CTkLabel(self, text="Date (YYYY-MM-DD, blank=today)").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.date_entry = ctk.CTkEntry(self, width=200)
        self.date_entry.grid(row=6, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self, text="Remarks").grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.remarks_entry = ctk.CTkEntry(self, width=350)
        self.remarks_entry.grid(row=7, column=1, padx=10, pady=5, sticky="we")

        ctk.CTkButton(self, text="Log Usage", command=self.log_usage).grid(row=8, column=0, columnspan=2, padx=10, pady=20)

        self.refresh_locations()

    def refresh_locations(self):
        if supabase is None:
            return
        try:
            res = supabase.table("locations").select("*").order("display_name").execute()
            self.locations = res.data
            names = [loc["display_name"] for loc in self.locations]
            self.location_combo.configure(values=names)
            if names:
                self.location_combo.set(names[0])
                self.update_components()
        except Exception:
            pass

    def get_selected_location_id(self) -> Optional[int]:
        current = self.location_combo.get()
        for loc in self.locations:
            if loc["display_name"] == current:
                return loc["id"]
        return None

    def update_components(self, event=None):
        if supabase is None:
            return
        loc_id = self.get_selected_location_id()
        if loc_id is None:
            return
        term = self.search_entry.get().strip().lower()
        try:
            res = supabase.table("stocks").select(
                "id, quantity, components(id, component_name_raw, part_number_raw)"
            ).eq("location_id", loc_id).execute()
            self.components_cache = []
            display_values = []
            for row in res.data:
                comp = row["components"]
                name_pretty = pretty_name(comp["component_name_raw"])
                part_pretty = pretty_name(comp["part_number_raw"])
                disp = f"{name_pretty} ({part_pretty}) - Qty: {row['quantity']}"
                if term and term not in disp.lower():
                    continue
                self.components_cache.append(
                    {
                        "stock_id": row["id"],
                        "component_id": comp["id"],
                        "quantity": row["quantity"],
                        "display": disp,
                    }
                )
                display_values.append(disp)
            self.comp_combo.configure(values=display_values)
            if display_values:
                self.comp_combo.set(display_values[0])
        except Exception:
            pass

    def log_usage(self):
        user = self.user_combo.get().strip()
        loc_id = self.get_selected_location_id()
        qty_txt = self.qty_entry.get().strip()
        purpose = self.purpose_entry.get().strip()
        remarks = self.remarks_entry.get().strip()
        date_txt = self.date_entry.get().strip()

        if not user or not qty_txt.isdigit() or loc_id is None:
            messagebox.showerror("Error", "User, location, and integer quantity are required.")
            return

        qty = int(qty_txt)

        if date_txt:
            try:
                use_date = datetime.date.fromisoformat(date_txt)
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
                return
        else:
            use_date = datetime.date.today()

        label = self.comp_combo.get()
        if not label:
            messagebox.showerror("Error", "Select a component.")
            return

        chosen = None
        for item in self.components_cache:
            if item["display"] == label:
                chosen = item
                break

        if chosen is None:
            messagebox.showerror("Error", "Component not found.")
            return

        if qty > chosen["quantity"]:
            messagebox.showerror("Error", f"Requested {qty}, but only {chosen['quantity']} available at this location.")
            return

        ts = now_ts()

        mv_data = {
            "component_id": chosen["component_id"],
            "from_location_id": loc_id,
            "to_location_id": None,
            "quantity": qty,
            "movement_type": "USE",
            "user_name": user,
            "purpose": purpose,
            "remarks": remarks,
            "movement_date": use_date.isoformat(),
            "created_at": ts,
        }
        queue_or_run("stock_movements", mv_data, "insert")

        new_qty = chosen["quantity"] - qty
        queue_or_run("stocks", {"quantity": new_qty, "updated_at": ts}, "update", chosen["stock_id"])

        messagebox.showinfo("Done", "Usage logged (queued if offline).")
        self.qty_entry.delete(0, "end")
        self.purpose_entry.delete(0, "end")
        self.date_entry.delete(0, "end")
        self.remarks_entry.delete(0, "end")
        self.update_components()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("themes/black_white.json")

        self.title("Smart Storage Management System")
        self.geometry("1100x650")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="Smart Storage", font=("Arial", 18, "bold")).pack(padx=20, pady=20)

        self.add_button = ctk.CTkButton(self.sidebar, text="ADD", command=self.show_add)
        self.add_button.pack(padx=10, pady=10, fill="x")

        self.manage_button = ctk.CTkButton(self.sidebar, text="MANAGE", command=self.show_manage)
        self.manage_button.pack(padx=10, pady=10, fill="x")

        self.use_button = ctk.CTkButton(self.sidebar, text="USE", command=self.show_use)
        self.use_button.pack(padx=10, pady=10, fill="x")

        self.status_label = ctk.CTkLabel(self.sidebar, text="Checking connection...")
        self.status_label.pack(side="bottom", padx=10, pady=10)

        self.container = ctk.CTkFrame(self)
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.add_page = AddPage(self.container)
        self.manage_page = ManagePage(self.container)
        self.use_page = UsePage(self.container)

        for page in (self.add_page, self.manage_page, self.use_page):
            page.grid(row=0, column=0, sticky="nsew")

        self.show_add()
        self.after(1000, self.update_status)

    def show_add(self):
        self.add_page.refresh_locations()
        self.add_page.tkraise()

    def show_manage(self):
        self.manage_page.refresh_locations()
        self.manage_page.tkraise()

    def show_use(self):
        self.use_page.refresh_locations()
        self.use_page.tkraise()

    def update_status(self):
        if online_flag:
            self.status_label.configure(text=f"Online (Queued: {len(offline_queue)})")
        else:
            self.status_label.configure(text=f"Offline (Queued: {len(offline_queue)})")
        self.after(2000, self.update_status)


if __name__ == "__main__":
    threading.Thread(target=background_sync, daemon=True).start()
    init_supabase()
    app = App()
    app.mainloop()
