import streamlit as st
from app import (
    get_all_components,
    upload_component_image,
    apply_action
)
from db_local import add_offline_action
from sync_engine import is_online, new_client_action_id, register_client_action
from helpers import normalize_component_text, display_component_text, build_component_key
from config import DEFAULT_MINIMUM_STOCK

st.title("➕ ADD COMPONENT")

all_components = get_all_components()
component_names_existing = sorted(list(set([c["component_name"] for c in all_components])))

st.subheader("Add New / Existing Component")

raw_name = st.text_input("Component Name")
part_number_input = st.text_input("Part Number / Value")
vendor_name = st.text_input("Vendor Name")
quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
purpose = st.text_area("Purpose of Purchase")
remarks = st.text_area("Remarks")
minimum_stock = st.number_input("Minimum Components Threshold", min_value=0, value=DEFAULT_MINIMUM_STOCK, step=1)
photo = st.file_uploader("Component Photo", type=["png", "jpg", "jpeg"])

if raw_name:
    normalized_name = normalize_component_text(raw_name)
    similar = [
        display_component_text(c["component_name"])
        for c in all_components
        if normalized_name in c["component_name"]
    ]
    similar = sorted(list(set(similar)))
    if similar:
        st.info("Similar existing components:")
        st.write(", ".join(similar))

if st.button("Add Component"):
    if not raw_name.strip():
        st.error("Component name is required")
        st.stop()

    component_name = normalize_component_text(raw_name)
    part_number = normalize_component_text(part_number_input)
    component_key = build_component_key(component_name, part_number)

    image_url = None
    if is_online() and photo is not None:
        try:
            image_url = upload_component_image(photo, component_key)
        except Exception as e:
            st.warning(f"Image upload failed: {e}")

    payload = {
        "component_key": component_key,
        "component_name": component_name,
        "component_name_display": display_component_text(component_name),
        "part_number": part_number,
        "part_number_display": display_component_text(part_number),
        "vendor_name": vendor_name.strip(),
        "quantity": int(quantity),
        "purpose_of_purchase": purpose.strip(),
        "remarks": remarks.strip(),
        "minimum_stock": int(minimum_stock),
        "image_url": image_url
    }

    client_action_id = new_client_action_id()

    if is_online():
        try:
            apply_action("ADD_COMPONENT", payload)
            register_client_action(client_action_id, "ADD_COMPONENT", payload)
            st.success("Component added successfully")
        except Exception as e:
            st.error(f"Failed to add component: {e}")
    else:
        add_offline_action(client_action_id, "ADD_COMPONENT", payload)
        st.warning("Offline mode: component saved locally and will sync when internet returns.")
