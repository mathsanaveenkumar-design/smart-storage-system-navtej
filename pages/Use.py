import streamlit as st
from datetime import datetime
from app import get_all_components, get_employees, apply_action
from db_local import add_offline_action
from sync_engine import is_online, new_client_action_id, register_client_action
from helpers import display_component_text, today_str

st.title("📤 USE COMPONENT")

components = get_all_components()
employees = get_employees()

if not employees:
    st.warning("No employees found. Add employees in Supabase table first.")

component_map = {
    f"{display_component_text(c['component_name'])} | {display_component_text(c.get('part_number', ''))} | Qty: {c['quantity']}": c
    for c in components if int(c["quantity"]) > 0
}

selected_employee = st.selectbox("User / Employee", employees if employees else [])
selected_component_label = st.selectbox("Component Willing to Use", list(component_map.keys()) if component_map else [])
quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
purpose = st.text_area("Purpose")
use_date = st.date_input("Date of Using")
remarks = st.text_area("Remarks")

if st.button("Use Component"):
    if not selected_component_label:
        st.error("Select a component")
        st.stop()

    component = component_map[selected_component_label]

    payload = {
        "component_id": component["id"],
        "employee_name": selected_employee,
        "quantity": int(quantity),
        "purpose": purpose.strip(),
        "transaction_date": str(use_date) if use_date else today_str(),
        "remarks": remarks.strip()
    }

    client_action_id = new_client_action_id()

    if is_online():
        try:
            apply_action("USE_COMPONENT", payload)
            register_client_action(client_action_id, "USE_COMPONENT", payload)
            st.success("Component usage recorded successfully")
        except Exception as e:
            st.error(f"Failed: {e}")
    else:
        add_offline_action(client_action_id, "USE_COMPONENT", payload)
        st.warning("Offline mode: usage saved locally and will sync later.")
