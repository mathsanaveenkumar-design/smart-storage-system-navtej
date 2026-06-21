import os
import datetime
import time
from typing import List, Dict, Any, Optional

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Optional[Client] = None
offline_queue: List[Dict[str, Any]] = []
online_flag: bool = False


def normalize_key(text: str) -> str:
    return text.strip().upper().replace(" ", "_")


def pretty_name(text: Optional[str]) -> str:
    if not text:
        return ""
    t = text.replace("_", " ").lower().strip()
    return " ".join(w.capitalize() for w in t.split())


def now_ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def init_supabase():
    global supabase, online_flag
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.table("components").select("id").limit(1).execute()
        supabase = client
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


def background_sync_loop():
    global supabase, online_flag, offline_queue
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


# ---------- Dashboard helpers ----------

def get_total_items() -> int:
    """Sum of all quantities in stocks."""
    if supabase is None:
        return 0
    try:
        res = supabase.table("stocks").select("quantity").execute()
        return sum((row.get("quantity") or 0) for row in res.data)
    except Exception:
        return 0


def get_low_stock_count(threshold: int = 5) -> int:
    """Count components with total quantity below threshold."""
    if supabase is None:
        return 0
    try:
        res = supabase.rpc("get_component_totals").execute()
        return sum(1 for row in res.data if (row.get("total_qty") or 0) <= threshold)
    except Exception:
        # Fallback: simple sum by stocks
        try:
            stocks = supabase.table("stocks").select("component_id, quantity").execute().data
            totals = {}
            for row in stocks:
                cid = row["component_id"]
                totals[cid] = totals.get(cid, 0) + (row.get("quantity") or 0)
            return sum(1 for v in totals.values() if v <= threshold)
        except Exception:
            return 0


def get_recent_movements(limit: int = 10) -> List[Dict[str, Any]]:
    if supabase is None:
        return []
    try:
        res = supabase.table("stock_movements").select("*").order("created_at", desc=True).limit(limit).execute()
        return res.data
    except Exception:
        return []

# ---------- Locations & components for ADD page ----------

def get_all_locations() -> list[dict]:
    if supabase is None:
        return []
    try:
        res = supabase.table("locations").select("*").order("display_name").execute()
        return res.data
    except Exception:
        return []


def ensure_location(rack_name: str, shelf_name: str, position: str | None = None) -> int | None:
    """
    Ensure a location exists for given rack/shelf/position, return its id.
    We encode location_key as RACK_SHELF_POSITION or RACK_SHELF if no position.
    """
    if supabase is None:
        return None

    rack_key = normalize_key(rack_name)
    shelf_key = normalize_key(shelf_name)
    if position:
        pos_key = normalize_key(position)
        loc_key = f"{rack_key}_{shelf_key}_{pos_key}"
        display = f"{pretty_name(rack_key)} / {pretty_name(shelf_key)} / {pretty_name(pos_key)}"
    else:
        loc_key = f"{rack_key}_{shelf_key}"
        display = f"{pretty_name(rack_key)} / {pretty_name(shelf_key)}"

    try:
        res = supabase.table("locations").select("*").eq("location_key", loc_key).execute()
        if res.data:
            return res.data[0]["id"]
        data = {
            "location_key": loc_key,
            "display_name": display,
            "created_at": now_ts()
        }
        queue_or_run("locations", data, "insert")
        # read back
        res2 = supabase.table("locations").select("id").eq("location_key", loc_key).single().execute()
        return res2.data["id"]
    except Exception:
        return None


def upsert_component_and_receive_stock(
    vendor: str,
    comp_name: str,
    part_number: str | None,
    qty: int,
    purpose: str,
    remarks: str,
    location_id: int,
    user_name: str = "SYSTEM"
) -> None:
    """
    Upsert component in components, upsert stocks at location, add stock_movements row (ADD).
    """
    if supabase is None:
        # offline: we just queue a generic components insert; no guarantees but keeps queueing
        ts = now_ts()
        cname_raw = normalize_key(comp_name)
        part_raw = normalize_key(part_number) if part_number else None
        comp_key = cname_raw + "_" + (part_raw if part_raw else "NO_PART")
        data_comp = {
            "component_key": comp_key,
            "component_name_raw": cname_raw,
            "part_number_raw": part_raw,
            "vendor_name": vendor,
            "purpose_of_purchase": purpose,
            "remarks": remarks,
            "created_at": ts,
            "updated_at": ts
        }
        queue_or_run("components", data_comp, "insert")
        return

    ts = now_ts()
    cname_raw = normalize_key(comp_name)
    part_raw = normalize_key(part_number) if part_number else None
    comp_key = cname_raw + "_" + (part_raw if part_raw else "NO_PART")

    comp_id = None
    try:
        res = supabase.table("components").select("*").eq("component_key", comp_key).execute()
        if res.data:
            comp = res.data[0]
            comp_id = comp["id"]
            update_data = {
                "vendor_name": vendor,
                "purpose_of_purchase": purpose,
                "remarks": remarks,
                "updated_at": ts,
            }
            queue_or_run("components", update_data, "update", comp_id)
        else:
            insert_data = {
                "component_key": comp_key,
                "component_name_raw": cname_raw,
                "part_number_raw": part_raw,
                "vendor_name": vendor,
                "purpose_of_purchase": purpose,
                "remarks": remarks,
                "created_at": ts,
                "updated_at": ts,
            }
            queue_or_run("components", insert_data, "insert")
            res2 = supabase.table("components").select("id").eq("component_key", comp_key).single().execute()
            comp_id = res2.data["id"]
    except Exception:
        return

    if comp_id is None:
        return

    # upsert into stocks
    try:
        res = supabase.table("stocks").select("*").eq("component_id", comp_id).eq("location_id", location_id).execute()
        if res.data:
            row = res.data[0]
            new_qty = (row["quantity"] or 0) + qty
            queue_or_run("stocks", {"quantity": new_qty, "updated_at": ts}, "update", row["id"])
        else:
            queue_or_run(
                "stocks",
                {"component_id": comp_id, "location_id": location_id, "quantity": qty, "updated_at": ts},
                "insert",
            )
    except Exception:
        pass

    # add stock_movements
    mv_data = {
        "component_id": comp_id,
        "from_location_id": None,
        "to_location_id": location_id,
        "quantity": qty,
        "movement_type": "ADD",
        "user_name": user_name,
        "purpose": purpose,
        "remarks": remarks,
        "movement_date": datetime.date.today().isoformat(),
        "created_at": ts,
    }
    queue_or_run("stock_movements", mv_data, "insert")
