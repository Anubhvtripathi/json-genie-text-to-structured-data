from __future__ import annotations

import json

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from src.json_genie.dynamic_schema import build_model_from_json_schema
from src.json_genie.extractors import ExtractionResult, extract_structured_data
from src.json_genie.sample_data import SAMPLE_TEXTS, USER_SCHEMA_EXAMPLE
from src.json_genie.schemas import DOCUMENT_MODELS
from src.json_genie.utils import validation_errors_to_rows


load_dotenv()

st.set_page_config(
    page_title="JSON Genie",
    page_icon="{}",
    layout="wide",
)

st.title("JSON Genie")
st.caption("Paste unstructured text and get clean, schema-validated JSON.")

with st.sidebar:
    st.header("Schema")
    document_type = st.selectbox(
        "Document type",
        ["Invoice", "Email", "Job Post", "Custom Schema"],
    )
    use_llm = st.toggle(
        "Use Groq extraction",
        value=False,
        help="Requires GROQ_API_KEY in your .env file or Streamlit secrets.",
    )

    st.divider()
    st.subheader("Try a sample")
    sample_key = st.selectbox("Sample text", list(SAMPLE_TEXTS.keys()))

if document_type == "Custom Schema":
    left, right = st.columns([1, 1])
    with left:
        raw_schema = st.text_area(
            "JSON schema",
            value=json.dumps(USER_SCHEMA_EXAMPLE, indent=2),
            height=340,
        )
    with right:
        st.write("Custom schemas support string, integer, number, boolean, array, and object fields.")
        st.json(USER_SCHEMA_EXAMPLE)

    try:
        schema_dict = json.loads(raw_schema)
        model = build_model_from_json_schema("CustomDocument", schema_dict)
        schema_error = None
    except Exception as exc:
        model = None
        schema_error = str(exc)
else:
    model = DOCUMENT_MODELS[document_type]
    schema_error = None

default_text = SAMPLE_TEXTS.get(sample_key, "")
input_text = st.text_area("Unstructured text", value=default_text, height=260)

extract_clicked = st.button("Extract JSON", type="primary", use_container_width=True)

if schema_error:
    st.error(f"Schema error: {schema_error}")

if extract_clicked:
    if not input_text.strip():
        st.warning("Paste some text first.")
    elif model is None:
        st.error("Fix the schema before extracting.")
    else:
        with st.spinner("Extracting and validating..."):
            result: ExtractionResult = extract_structured_data(
                text=input_text,
                model=model,
                document_type=document_type,
                prefer_llm=use_llm,
            )

        result_col, meta_col = st.columns([2, 1])

        with result_col:
            st.subheader("Validated JSON")
            st.json(result.data)

            st.download_button(
                "Download JSON",
                data=json.dumps(result.data, indent=2),
                file_name=f"{document_type.lower().replace(' ', '_')}_extraction.json",
                mime="application/json",
                use_container_width=True,
            )

        with meta_col:
            st.subheader("Status")
            if result.valid:
                st.success("Schema validation passed.")
            else:
                st.warning("Returned partial JSON with validation notes.")

            st.write(f"Extractor: `{result.extractor}`")

            if result.errors:
                st.subheader("Validation Issues")
                st.dataframe(validation_errors_to_rows(result.errors), use_container_width=True)

            if result.raw_response:
                with st.expander("Raw model output"):
                    st.code(result.raw_response, language="json")
