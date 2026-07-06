from __future__ import annotations

import json
from datetime import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.json_genie.dynamic_schema import build_model_from_json_schema
from src.json_genie.extractors import ExtractionResult, extract_structured_data
from src.json_genie.sample_data import SAMPLE_TEXTS, USER_SCHEMA_EXAMPLE
from src.json_genie.schemas import DOCUMENT_MODELS
from src.json_genie.utils import (
    validation_errors_to_rows,
    results_to_dataframe,
    dataframe_to_csv,
    dataframe_to_excel
)
from src.json_genie.file_reader import extract_text_from_file
from src.json_genie.schema_builder import render_schema_builder

load_dotenv()

# ── Session State Initializations ──────────────────────────────────────────────
if "extraction_history" not in st.session_state:
    st.session_state["extraction_history"] = []

if "raw_input_text" not in st.session_state:
    st.session_state["raw_input_text"] = ""

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JSON Genie - Advanced Text to Structured Data",
    page_icon="🧞",
    layout="wide",
)

# ── Custom CSS for Premium Design ──────────────────────────────────────────────
st.markdown("""
<style>
    /* Gradient headers */
    .main-title {
        font-size: 3rem !important;
        font-weight: 800 !important;
        background: linear-gradient(90deg, #FF4B4B, #FF8F8F, #4A90E2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem !important;
    }
    
    /* Sleek card container */
    .metric-card {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #FF4B4B;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #888888;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<h1 class="main-title">🧞 JSON Genie</h1>', unsafe_allow_html=True)
st.caption(
    "Transform unstructured files and text into structured, validated JSON, CSV, or Excel formats using Rule-based or AI extraction."
)
st.divider()

# ── Sidebar Settings ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    document_type = st.selectbox(
        "Document Type",
        ["Invoice", "Email", "Job Post", "Custom Schema"],
        help="Select the schema model used for validation.",
    )

    use_llm = st.toggle(
        "Use Groq AI Extraction",
        value=False,
        help="Uses Llama-3.3 on Groq Cloud. Falls back to Rule-based extraction if key missing or limit exceeded.",
    )

    # 🌍 Multi-language Selector (Groq AI only)
    target_language = st.selectbox(
        "Target Language 🌍",
        ["English", "Spanish", "French", "German", "Hindi", "Japanese", "Chinese", "Arabic"],
        index=0,
        help="The language in which the extracted data values should be returned (AI only)."
    )

    st.divider()
    
    # Visual Schema Builder or Custom Schema raw edit
    schema_mode = "Visual"
    if document_type == "Custom Schema":
        schema_mode = st.radio("Schema Builder Mode", ["Visual Builder", "Raw JSON Schema"], horizontal=True)

    # 📋 Sample Loader
    st.subheader("📋 Load Sample Text")
    if document_type == "Invoice":
        relevant_samples = ["Invoice", "Messy Missing Fields"]
    elif document_type == "Email":
        relevant_samples = ["Email"]
    elif document_type == "Job Post":
        relevant_samples = ["Job Post"]
    else:
        relevant_samples = list(SAMPLE_TEXTS.keys())

    sample_key = st.selectbox("Sample data source", relevant_samples)

    if st.button("Load Selected Sample", use_container_width=True):
        st.session_state["raw_input_text"] = SAMPLE_TEXTS.get(sample_key, "")
        st.toast(f"Loaded '{sample_key}' sample text!")

    st.divider()
    
    # 🕐 Extraction History Sidebar Panel
    st.subheader("🕐 Session History")
    if not st.session_state["extraction_history"]:
        st.caption("No extractions in this session yet.")
    else:
        for idx, item in enumerate(reversed(st.session_state["extraction_history"])):
            status_emoji = "✅" if item["valid"] else "⚠️"
            button_label = f"{status_emoji} {item['time']} - {item['doc_type']}"
            if st.button(button_label, key=f"hist_{idx}", use_container_width=True):
                st.session_state["raw_input_text"] = item["original_text"]
                st.toast(f"Reloaded history item from {item['time']}")
        if st.button("Clear History", type="secondary", use_container_width=True):
            st.session_state["extraction_history"] = []
            st.rerun()

    st.divider()
    st.markdown(
        "**GitHub**: [json-genie](https://github.com/Anubhvtripathi/json-genie-text-to-structured-data)"
    )

# ── Dynamic Model & Custom Schema Resolution ──────────────────────────────────
model = None
schema_error = None

if document_type == "Custom Schema":
    if schema_mode == "Visual Builder":
        custom_schema_dict = render_schema_builder()
        try:
            model = build_model_from_json_schema("CustomDocument", custom_schema_dict)
            st.success("✅ Visually built schema is valid.")
        except Exception as exc:
            model = None
            schema_error = f"Builder Error: {exc}"
    else:
        st.subheader("🛠️ Raw JSON Schema Editor")
        raw_schema = st.text_area(
            "JSON Schema Code",
            value=json.dumps(USER_SCHEMA_EXAMPLE, indent=2),
            height=250,
        )
        try:
            custom_schema_dict = json.loads(raw_schema)
            model = build_model_from_json_schema("CustomDocument", custom_schema_dict)
            st.success("✅ Raw JSON schema parsed and validated successfully.")
        except Exception as exc:
            model = None
            schema_error = f"Parse Error: {exc}"
else:
    model = DOCUMENT_MODELS[document_type]

# ── Main Tabs (Single Extract & Batch Process) ─────────────────────────────────
tab_single, tab_batch = st.tabs(["📄 Single Document", "📁 Batch Processing"])

# ── Tab 1: Single Document ─────────────────────────────────────────────────────
with tab_single:
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("📥 Input Text / Document")
        
        # File upload support
        uploaded_file = st.file_uploader(
            "Upload file (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt", "csv", "json"],
            key="single_file_uploader",
            help="Extracts text content directly from the selected file."
        )

        if uploaded_file is not None:
            file_key = f"read_{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get("last_read_file") != file_key:
                with st.spinner("Extracting text from file..."):
                    try:
                        file_bytes = uploaded_file.read()
                        extracted = extract_text_from_file(file_bytes, uploaded_file.name)
                        st.session_state["raw_input_text"] = extracted
                        st.session_state["last_read_file"] = file_key
                        st.toast(f"Extracted content from {uploaded_file.name}")
                    except Exception as e:
                        st.error(f"Error reading file: {e}")

        # Text input area
        input_text = st.text_area(
            "Edit or paste unstructured text below:",
            value=st.session_state["raw_input_text"],
            height=280,
            key="input_text_area",
            placeholder="Paste text or upload a file to start..."
        )
        # Keep session state updated with manual edits
        st.session_state["raw_input_text"] = input_text

        if schema_error:
            st.error(f"⚠️ Schema Error: {schema_error}")

        extract_clicked = st.button("⚡ Extract Structured Data", type="primary", use_container_width=True)

    with right_col:
        st.subheader("📤 Extracted structured Output")
        
        if extract_clicked:
            if not input_text.strip():
                st.warning("⚠️ Please provide some input text first.")
            elif model is None:
                st.error("❌ Fix the schema errors before running extraction.")
            else:
                with st.spinner("Processing & validating data schema..."):
                    start_time = datetime.now()
                    result: ExtractionResult = extract_structured_data(
                        text=input_text,
                        model=model,
                        document_type=document_type,
                        prefer_llm=use_llm,
                        language=target_language
                    )
                    end_time = datetime.now()
                
                # Add to history list
                st.session_state["extraction_history"].append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "doc_type": document_type,
                    "original_text": input_text,
                    "result": result.data,
                    "valid": result.valid
                })

                # Calculate fields completeness & stats
                total_fields = len(result.data)
                non_null_fields = sum(1 for v in result.data.values() if v not in (None, [], {}, ""))
                completeness_pct = int((non_null_fields / total_fields) * 100) if total_fields > 0 else 0

                # Top stats cards
                stat_col1, stat_col2, stat_col3 = st.columns(3)
                with stat_col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{"✅ PASS" if result.valid else "⚠️ WARN"}</div>
                        <div class="metric-label">Validation Status</div>
                    </div>
                    """, unsafe_allow_html=True)
                with stat_col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{completeness_pct}%</div>
                        <div class="metric-label">Completeness</div>
                    </div>
                    """, unsafe_allow_html=True)
                with stat_col3:
                    method_used = "Groq AI" if "Groq" in result.extractor else "Rule-based"
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value" style="font-size: 1.4rem; padding-top: 5px;">{method_used}</div>
                        <div class="metric-label">Extraction Engine</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Show structured output
                st.json(result.data)

                # Convert to flat pandas dataframe for CSV/Excel download
                try:
                    df = results_to_dataframe(result.data)
                    csv_bytes = dataframe_to_csv(df)
                    excel_bytes = dataframe_to_excel(df)
                except Exception as e:
                    df = None
                    st.error(f"Could not convert data to flat table format: {e}")

                # Download Options
                dl_col1, dl_col2, dl_col3 = st.columns(3)
                with dl_col1:
                    st.download_button(
                        "⬇️ Download JSON",
                        data=json.dumps(result.data, indent=2),
                        file_name=f"{document_type.lower().replace(' ', '_')}_extracted.json",
                        mime="application/json",
                        use_container_width=True
                    )
                with dl_col2:
                    if df is not None:
                        st.download_button(
                            "⬇️ Download CSV",
                            data=csv_bytes,
                            file_name=f"{document_type.lower().replace(' ', '_')}_extracted.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                with dl_col3:
                    if df is not None:
                        st.download_button(
                            "⬇️ Download Excel",
                            data=excel_bytes,
                            file_name=f"{document_type.lower().replace(' ', '_')}_extracted.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                # Validation Issues Table
                if result.errors:
                    st.warning("⚠️ Schema Validation Details:")
                    st.dataframe(
                        validation_errors_to_rows(result.errors),
                        use_container_width=True
                    )

                # Raw AI Output Expander
                if result.raw_response:
                    with st.expander("🔍 Show Raw LLM JSON"):
                        st.code(result.raw_response, language="json")
        else:
            st.info("💡 Paste document text or upload a file, then click 'Extract' to see results.")

# ── Tab 2: Batch Processing ───────────────────────────────────────────────────
with tab_batch:
    st.subheader("📁 Process Multiple Documents in Batch")
    st.write(
        "Upload multiple files (PDF, DOCX, TXT). "
        "The app will extract data from each file using the selected schema settings and compile them into a unified table."
    )

    batch_files = st.file_uploader(
        "Upload multiple files",
        type=["pdf", "docx", "txt", "csv", "json"],
        accept_multiple_files=True,
        key="batch_files_uploader"
    )

    process_batch_clicked = st.button("⚡ Run Batch Extraction", type="primary", use_container_width=True)

    if process_batch_clicked:
        if not batch_files:
            st.warning("⚠️ Please upload at least one file for batch processing.")
        elif model is None:
            st.error("❌ Please fix the schema configurations before running.")
        else:
            batch_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, file in enumerate(batch_files):
                status_text.text(f"Processing file {idx+1}/{len(batch_files)}: {file.name}...")
                try:
                    # Read and extract text
                    file_bytes = file.read()
                    file_text = extract_text_from_file(file_bytes, file.name)
                    
                    # Run extraction
                    res: ExtractionResult = extract_structured_data(
                        text=file_text,
                        model=model,
                        document_type=document_type,
                        prefer_llm=use_llm,
                        language=target_language
                    )
                    
                    # Format result record
                    record = {
                        "filename": file.name,
                        "valid": res.valid,
                        **res.data
                    }
                    batch_results.append(record)
                except Exception as exc:
                    st.error(f"Error processing {file.name}: {exc}")
                
                # Update progress bar
                progress_bar.progress((idx + 1) / len(batch_files))

            status_text.text("🎉 Batch processing complete!")
            
            if batch_results:
                st.subheader("📊 Combined Batch Results")
                
                # Convert results to dataframe
                try:
                    batch_df = results_to_dataframe(batch_results)
                    st.dataframe(batch_df, use_container_width=True)
                    
                    # File downloads
                    csv_batch = dataframe_to_csv(batch_df)
                    excel_batch = dataframe_to_excel(batch_df)
                    
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        st.download_button(
                            "⬇️ Download Combined CSV",
                            data=csv_batch,
                            file_name=f"batch_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    with col_dl2:
                        st.download_button(
                            "⬇️ Download Combined Excel",
                            data=excel_batch,
                            file_name=f"batch_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                except Exception as err:
                    st.error(f"Error compiling batch results table: {err}")
