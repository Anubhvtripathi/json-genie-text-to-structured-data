from __future__ import annotations

import json

import streamlit as st
from dotenv import load_dotenv

from src.json_genie.dynamic_schema import build_model_from_json_schema
from src.json_genie.extractors import ExtractionResult, extract_structured_data
from src.json_genie.sample_data import SAMPLE_TEXTS, USER_SCHEMA_EXAMPLE
from src.json_genie.schemas import DOCUMENT_MODELS
from src.json_genie.utils import validation_errors_to_rows

load_dotenv()

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JSON Genie",
    page_icon="🧞",
    layout="wide",
)

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("🧞 JSON Genie")
st.caption(
    "Turn messy text — invoices, emails, job posts, or any custom format — "
    "into clean, schema-validated JSON instantly."
)
st.divider()

# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    document_type = st.selectbox(
        "Document type",
        ["Invoice", "Email", "Job Post", "Custom Schema"],
        help="Choose the type of document you want to extract data from.",
    )

    use_llm = st.toggle(
        "Use Groq AI extraction",
        value=False,
        help="Uses the Groq LLM for smarter extraction. Requires a GROQ_API_KEY.",
    )

    st.divider()
    st.subheader("📋 Load a sample")

    # Only show samples relevant to the selected document type
    if document_type == "Invoice":
        relevant_samples = ["Invoice", "Messy Missing Fields"]
    elif document_type == "Email":
        relevant_samples = ["Email"]
    elif document_type == "Job Post":
        relevant_samples = ["Job Post"]
    else:
        relevant_samples = list(SAMPLE_TEXTS.keys())

    sample_key = st.selectbox("Sample text", relevant_samples)

    if st.button("Load sample", use_container_width=True):
        st.session_state["loaded_sample"] = SAMPLE_TEXTS.get(sample_key, "")

    st.divider()
    st.markdown(
        "**GitHub**: [json-genie](https://github.com/Anubhvtripathi/json-genie-text-to-structured-data)"
    )

# ── Custom Schema editor ────────────────────────────────────────────────────────
if document_type == "Custom Schema":
    st.subheader("🛠️ Define your JSON schema")
    st.caption(
        "Write a JSON schema with a `properties` object. "
        "Supported types: `string`, `integer`, `number`, `boolean`, `array`, `object`."
    )
    raw_schema = st.text_area(
        "JSON Schema",
        value=json.dumps(USER_SCHEMA_EXAMPLE, indent=2),
        height=300,
        label_visibility="collapsed",
    )
    try:
        schema_dict = json.loads(raw_schema)
        model = build_model_from_json_schema("CustomDocument", schema_dict)
        schema_error = None
        st.success("✅ Schema is valid.")
    except Exception as exc:
        model = None
        schema_error = str(exc)
else:
    model = DOCUMENT_MODELS[document_type]
    schema_error = None

# ── Input area ──────────────────────────────────────────────────────────────────
default_text = st.session_state.pop("loaded_sample", "")
input_text = st.text_area(
    "📄 Paste your unstructured text here",
    value=default_text,
    height=240,
    placeholder="Paste an invoice, email, job post, or any document text here...",
)

if schema_error:
    st.error(f"⚠️ Schema error: {schema_error}")

extract_clicked = st.button("⚡ Extract JSON", type="primary", use_container_width=True)

# ── Result ──────────────────────────────────────────────────────────────────────
if extract_clicked:
    if not input_text.strip():
        st.warning("⚠️ Please paste some text before extracting.")
    elif model is None:
        st.error("❌ Fix the schema errors before extracting.")
    else:
        with st.spinner("Extracting and validating..."):
            result: ExtractionResult = extract_structured_data(
                text=input_text,
                model=model,
                document_type=document_type,
                prefer_llm=use_llm,
            )

        st.divider()
        result_col, meta_col = st.columns([2, 1])

        with result_col:
            st.subheader("📦 Extracted JSON")
            st.json(result.data)
            st.download_button(
                "⬇️ Download JSON",
                data=json.dumps(result.data, indent=2),
                file_name=f"{document_type.lower().replace(' ', '_')}_extraction.json",
                mime="application/json",
                use_container_width=True,
            )

        with meta_col:
            st.subheader("✅ Validation")
            if result.valid:
                st.success("All fields validated successfully.")
            else:
                st.warning("Partial extraction — some fields could not be validated.")

            method = "🤖 Groq AI" if "Groq" in result.extractor else "📐 Rule-based"
            st.info(f"Method: {method}")

            if result.errors:
                st.subheader("⚠️ Issues")
                st.dataframe(
                    validation_errors_to_rows(result.errors),
                    use_container_width=True,
                )

            if result.raw_response:
                with st.expander("🔍 Raw model output"):
                    st.code(result.raw_response, language="json")
