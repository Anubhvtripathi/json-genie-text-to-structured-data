from __future__ import annotations

import streamlit as st

def render_schema_builder() -> dict:
    """
    Renders a visual UI to construct a JSON Schema.
    Returns the generated JSON Schema dictionary.
    """
    st.subheader("🛠️ Visual Schema Builder")
    st.caption("Define the fields you want to extract from your documents without writing code.")

    # Initialize schema fields in session state if not present
    if "schema_fields" not in st.session_state:
        st.session_state["schema_fields"] = [
            {"name": "document_date", "type": "string", "description": "The date of the document", "required": True},
            {"name": "total_amount", "type": "number", "description": "The total amount or cost mentioned", "required": False},
        ]

    # Initialize schema title in session state if not present
    if "schema_title" not in st.session_state:
        st.session_state["schema_title"] = "CustomDocument"

    # Schema Title Input
    st.session_state["schema_title"] = st.text_input(
        "Schema name (no spaces)",
        value=st.session_state["schema_title"],
        placeholder="e.g. Invoice, Receipt, SupportTicket"
    ).strip().replace(" ", "")

    if not st.session_state["schema_title"]:
        st.session_state["schema_title"] = "CustomDocument"

    # Display and edit fields
    fields = st.session_state["schema_fields"]
    new_fields = []
    
    st.markdown("### Fields")
    
    for i, field in enumerate(fields):
        with st.container():
            # Use columns for field attributes
            col1, col2, col3, col4, col5 = st.columns([2, 1.5, 3.5, 1, 1])
            
            with col1:
                name = st.text_input(
                    "Field Name",
                    value=field["name"],
                    key=f"field_name_{i}",
                    placeholder="e.g. client_name"
                ).strip().lower().replace(" ", "_")
            
            with col2:
                field_type = st.selectbox(
                    "Type",
                    options=["string", "integer", "number", "boolean", "array"],
                    index=["string", "integer", "number", "boolean", "array"].index(field["type"]),
                    key=f"field_type_{i}"
                )
            
            with col3:
                description = st.text_input(
                    "Description / Instructions",
                    value=field["description"],
                    key=f"field_desc_{i}",
                    placeholder="What should the AI look for?"
                )
            
            with col4:
                # Align checkbox nicely
                st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
                required = st.checkbox(
                    "Required",
                    value=field["required"],
                    key=f"field_req_{i}"
                )
            
            with col5:
                st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
                delete_clicked = st.button("🗑️", key=f"field_del_{i}", help="Delete field")

            if not delete_clicked:
                new_fields.append({
                    "name": name,
                    "type": field_type,
                    "description": description,
                    "required": required
                })
            
            st.divider()

    st.session_state["schema_fields"] = new_fields

    # Add field button
    if st.button("➕ Add New Field"):
        st.session_state["schema_fields"].append({
            "name": f"new_field_{len(st.session_state['schema_fields']) + 1}",
            "type": "string",
            "description": "",
            "required": False
        })
        st.rerun()

    # Generate JSON Schema
    properties = {}
    required_fields = []

    for field in st.session_state["schema_fields"]:
        if not field["name"]:
            continue
            
        field_schema = {
            "type": field["type"],
            "description": field["description"]
        }
        
        if field["type"] == "array":
            # Default array items to string type
            field_schema["items"] = {"type": "string"}
            
        properties[field["name"]] = field_schema
        
        if field["required"]:
            required_fields.append(field["name"])

    generated_schema = {
        "title": st.session_state["schema_title"],
        "type": "object",
        "properties": properties
    }
    
    if required_fields:
        generated_schema["required"] = required_fields

    return generated_schema
