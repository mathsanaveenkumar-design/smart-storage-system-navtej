import streamlit as st
import pandas as pd
from datetime import datetime
from supabase_client import supabase
from db_local import init_local_db, add_offline_action
from sync_engine import sync_pending_actions, is_online, new_client_action_id, register_client_action
from helpers import normalize_component_text, display_component_text, build_component_key, today_str
from config import DEFAULT_MINIMUM_STOCK, PHOTO_BUCKET
import uuid

st.set_page_config(
    page_title="Smart Storage Management System",
    page_icon="📦",
    layout="wide"
)

# ---------- CSS ----------
def load_css():
    st.markdown("""
    <style>
    .stApp {
        background-color: #ffffff;
        color: #000000;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1300px;
    }
    h1,h2,h3,h4,h5,h6,p,label,span,div {
        color: #000000 !important;
    }
    .stButton>button {
        background-color: #000000;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
    }
    .stTextInput>div>div>input,
    .stTextArea textarea,
    .stNumberInput input,
    .stDateInput input,
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #000000 !important;
        border-radius: 8px !important;
    }
    .card {
        border: 1px solid #000000;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        background-color: #f8f8f8;
    }
    .small-note {
        color: #444;
        font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

load_css()
init_local_db()

# ---------- DB FUNCTIONS ----------
def get_all_components():
    res = supabase.table("components").select("*").order("component_name").execute()
    return res.data or []

def get_component_by_key(component_key):
    res = supabase.table("components").select("*").eq("component_key", component_key).execute()
    data = res.data or []
    return data[0] if data else None

def get_component_by_id(component_id):
    res = supabase.table("components").select("*").eq("id", component_id).execute()
    data = res.data or []
    return data[0] if data else None

def get_component_locations():
    res = supabase.table("component_locations").select("*").execute()
    return res.data or []

def get_location_for_component(component_id):
    res = supabase.table("component_locations").select("*").eq("component_id", component_id).execute()
    data = res.data or []
    return data[0] if data else None

def get_employees():
    res = supabase.table("employees").select("*").order("employee_name").execute()
    data = res.data or []
    return [x["employee_name"] for x in data]

def upload_component_image(file, component_key):
    if file is None:
        return None

    file_ext = file.name.split(".")[-1]
    file_path = f"{component_key}/{uuid.uuid4()}.{file_ext}"

    file_bytes = file.read()

    supabase.storage.from_(PHOTO_BUCKET).upload(
        path=file_path,
        file=file_bytes,
        file_options={"content-type": file.type, "upsert": "true"}
    )

    public_url = supabase.storage.from_(PHOTO_BUCKET).get_public_url(file_path)
    return public_url

def create_or_update_component(payload):
    component_key = payload["component_key"]
    existing = get_component_by_key(component_key)

    if existing:
        new_qty = int(existing["quantity"]) + int(payload["quantity"])
        supabase.table("components").update({
            "quantity": new_qty,
            "vendor_name": payload.get("vendor_name"),
            "purpose_of_purchase": payload.get("purpose_of_purchase"),
            "remarks": payload.get("remarks"),
            "minimum_stock": payload.get("minimum_stock", DEFAULT_MINIMUM_STOCK),
            "image_url": payload.get("image_url") or existing.get("image_url")
        }).eq("id", existing["id"]).execute()

        component_id = existing["id"]
    else:
        ins = supabase.table("components").insert({
            "component_key": payload["component_key"],
            "component_name": payload["component_name"],
            "component_name_display": payload["component_name_display"],
            "part_number": payload["part_number"],
            "part_number_display": payload["part_number_display"],
            "vendor_name": payload.get("vendor_name"),
            "purpose_of_purchase": payload.get("purpose_of_purchase"),
            "remarks": payload.get("remarks"),
            "minimum_stock": payload.get("minimum_stock", DEFAULT_MINIMUM_STOCK),
            "quantity": payload["quantity"],
            "image_url": payload.get("image_url")
        }).execute()

        component_id = ins.data[0]["id"]

    # add stock transaction
    supabase.table("stock_transactions").insert({
        "component_id": component_id,
        "transaction_type": "ADD",
        "quantity": payload["quantity"],
        "vendor_name": payload.get("vendor_name"),
        "purpose": payload.get("purpose_of_purchase"),
        "remarks": payload.get("remarks"),
        "transaction_date": today_str()
    }).execute()

    return component_id

def update_component_location(component_id, rack_name, shelf_name, remarks=""):
    existing = get_location_for_component(component_id)
    if existing:
        supabase.table("component_locations").update({
            "rack_name": rack_name,
            "shelf_name": shelf_name,
            "remarks": remarks
        }).eq("component_id", component_id).execute()
    else:
        supabase.table("component_locations").insert({
            "component_id": component_id,
            "rack_name": rack_name,
            "shelf_name": shelf_name,
            "remarks": remarks
        }).execute()

def use_component(payload):
    component = get_component_by_id(payload["component_id"])
    if not component:
        raise Exception("Component not found")

    current_qty = int(component["quantity"])
    use_qty = int(payload["quantity"])

    if use_qty <= 0:
        raise Exception("Quantity must be greater than 0")
    if use_qty > current_qty:
        raise Exception("Insufficient stock")

    new_qty = current_qty - use_qty

    supabase.table("components").update({
        "quantity": new_qty
    }).eq("id", payload["component_id"]).execute()

    supabase.table("stock_transactions").insert({
        "component_id": payload["component_id"],
        "transaction_type": "USE",
        "quantity": use_qty,
        "employee_name": payload["employee_name"],
        "purpose": payload["purpose"],
        "remarks": payload.get("remarks"),
        "transaction_date": payload["transaction_date"]
    }).execute()

def apply_action(action_type, payload, from_sync=False):
    if action_type == "ADD_COMPONENT":
        create_or_update_component(payload)
    elif action_type == "UPDATE_LOCATION":
        update_component_location(
            payload["component_id"],
            payload["rack_name"],
            payload["shelf_name"],
            payload.get("remarks", "")
        )
    elif action_type == "USE_COMPONENT":
        use_component(payload)
    else:
        raise Exception("Unknown action type")

# ---------- AUTO SYNC ----------
try:
    synced = sync_pending_actions(apply_action)
except:
    synced = 0

# ---------- SIDEBAR ----------
st.sidebar.title("📦 Smart Storage")
st.sidebar.write("Black & White Inventory System")
online_status = "🟢 Online" if is_online() else "🔴 Offline"
st.sidebar.info(f"Status: {online_status}")
if synced:
    st.sidebar.success(f"Synced offline actions: {synced}")

st.title("Smart Storage Management System")
st.caption("Use the left sidebar to open ADD / MANAGE / USE pages.")
