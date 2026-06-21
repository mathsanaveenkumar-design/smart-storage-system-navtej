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
