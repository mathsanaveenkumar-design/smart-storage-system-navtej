import streamlit as st
import pandas as pd
from app import (
    get_all_components,
    get_location_for_component,
    update_component_location,
    apply_action
)
from db_local import add_offline_action
from sync_engine import is_online, new_client_action_id, register_client_action
from helpers import display_component_text

st.title("🛠️ MANAGE COMPONENTS")

components = get_all_components()

search = st.text_input("Search Component")

filtered = []
for c in components:
    name_disp = display_component_text(c["component_name"])
    part_disp = display_component_text(c.get("part_number", ""))
    if not search.strip():
        filtered.append(c)
    else:
        s = search.strip().lower()
        if s in name_disp.lower() or s in part_disp.lower() or s in c["component_key"].lower():
            filtered.append(c)

st.subheader(f"Components Found: {len(filtered)}")

for c in filtered:
    location = get_location_for_component(c["id"])
    rack = location["rack_name"] if location else ""
    shelf = location["shelf_name"] if location else ""
    loc_remarks = location["remarks"] if location else ""

    with st.container(border=True):
        col1, col2 = st.columns([1, 3])

        with col1:
            if c.get("image_url"):
                st.image(c["image_url"], width=150)
            else:
                st.write("No Image")

        with col2:
            st.markdown(f"### {display_component_text(c['component_name'])}")
            st.write(f"**Part / Value:** {display_component_text(c.get('part_number', ''))}")
            st.write(f"**Vendor:** {c.get('vendor_name', '')}")
            st.write(f"**Available Quantity:** {c['quantity']}")
            st.write(f"**Minimum Threshold:** {c.get('minimum_stock', 10)}")

            if int(c["quantity"]) <= int(c.get("minimum_stock", 10)):
                st.warning("Stock below minimum threshold!")

            rack_name = st.text_input(f"Rack Name - {c['id']}", value=rack)
            shelf_name = st.text_input(f"Shelf Name - {c['id']}", value=shelf)
            remarks = st.text_input(f"Location Remarks - {c['id']}", value=loc_remarks)

            if st.button(f"Save Location - {c['id']}"):
                payload = {
                    "component_id": c["id"],
                    "rack_name": rack_name.strip(),
                    "shelf_name": shelf_name.strip(),
                    "remarks": remarks.strip()
                }

                client_action_id = new_client_action_id()

                if is_online():
                    try:
                        apply_action("UPDATE_LOCATION", payload)
                        register_client_action(client_action_id, "UPDATE_LOCATION", payload)
                        st.success("Location updated")
                    except Exception as e:
                        st.error(str(e))
                else:
                    add_offline_action(client_action_id, "UPDATE_LOCATION", payload)
                    st.warning("Offline: location update queued for sync")
