from __future__ import annotations

import json
import os
from datetime import datetime
import pandas as pd
# pyrefly: ignore [missing-import]
import streamlit as st
# pyrefly: ignore [missing-import]
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

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JSON Genie — Text to Structured Data",
    page_icon="🧞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State Initializations ──────────────────────────────────────────────
if "extraction_history" not in st.session_state:
    st.session_state["extraction_history"] = []
if "raw_input_text" not in st.session_state:
    st.session_state["raw_input_text"] = ""
if "doc_type_card" not in st.session_state:
    st.session_state["doc_type_card"] = "Invoice"
if "total_processed" not in st.session_state:
    st.session_state["total_processed"] = 0
if "total_response_ms" not in st.session_state:
    st.session_state["total_response_ms"] = 0
if "last_valid" not in st.session_state:
    st.session_state["last_valid"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# ── Premium CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
/* ═══════════════════════════════════════════════════
   ROOT VARIABLES
═══════════════════════════════════════════════════ */
:root {
  --bg-base:        #0d0f14;
  --bg-surface:     #151820;
  --bg-surface2:    #1c2030;
  --bg-surface3:    #222638;
  --border:         rgba(99,102,241,0.15);
  --border-soft:    rgba(255,255,255,0.07);
  --indigo:         #6366f1;
  --indigo-dim:     rgba(99,102,241,0.12);
  --indigo-hover:   #5457e8;
  --indigo-glow:    rgba(99,102,241,0.35);
  --text-primary:   #e2e8f0;
  --text-secondary: #94a3b8;
  --text-muted:     #64748b;
  --green:          #22c55e;
  --green-dim:      rgba(34,197,94,0.12);
  --amber:          #f59e0b;
  --amber-dim:      rgba(245,158,11,0.12);
  --red:            #ef4444;
  --red-dim:        rgba(239,68,68,0.12);
  --radius-sm:      8px;
  --radius-md:      12px;
  --radius-lg:      16px;
  --radius-xl:      20px;
  --shadow-sm:      0 1px 3px rgba(0,0,0,0.4);
  --shadow-md:      0 4px 16px rgba(0,0,0,0.5);
  --shadow-lg:      0 8px 32px rgba(0,0,0,0.6);
  --shadow-glow:    0 0 32px rgba(99,102,241,0.15);
}

/* ═══════════════════════════════════════════════════
   BASE RESET & FONT
═══════════════════════════════════════════════════ */
html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
  -webkit-font-smoothing: antialiased;
}

.main .block-container {
  padding-top: 1rem !important;
  padding-bottom: 2rem !important;
  max-width: 1400px !important;
}

/* Hide default Streamlit header/footer/menu */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
.stDeployButton { display: none; }

/* ═══════════════════════════════════════════════════
   STICKY NAVIGATION BAR
═══════════════════════════════════════════════════ */
.genie-nav {
  position: sticky;
  top: 0;
  z-index: 9999;
  background: rgba(13,15,20,0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-soft);
  padding: 0 2rem;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0;
}

.genie-nav-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.genie-nav-logo span.emoji {
  font-size: 1.3rem;
}

.genie-nav-logo span.logo-text {
  background: linear-gradient(135deg, #818cf8, #6366f1 40%, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.genie-nav-links {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.genie-nav-link {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
  cursor: pointer;
}

.genie-nav-link:hover {
  color: var(--text-primary);
  background: var(--bg-surface2);
}

.genie-nav-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-icon-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  background: var(--bg-surface2);
  border: 1px solid var(--border-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.15s ease;
  color: var(--text-secondary);
}

.nav-icon-btn:hover {
  background: var(--bg-surface3);
  border-color: var(--border);
  color: var(--text-primary);
}

/* ═══════════════════════════════════════════════════
   HERO SECTION
═══════════════════════════════════════════════════ */
.hero-section {
  padding: 3.5rem 0 2.5rem;
  position: relative;
  overflow: hidden;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: -60%;
  left: 50%;
  transform: translateX(-50%);
  width: 900px;
  height: 500px;
  background: radial-gradient(ellipse, rgba(99,102,241,0.12) 0%, transparent 70%);
  pointer-events: none;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--indigo-dim);
  border: 1px solid rgba(99,102,241,0.3);
  color: #a5b4fc;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: 100px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 1.5rem;
  animation: fadeInDown 0.5s ease;
}

.hero-title {
  font-size: clamp(2.8rem, 5vw, 4.5rem) !important;
  font-weight: 800 !important;
  letter-spacing: -0.04em !important;
  line-height: 1.08 !important;
  margin: 0 0 1.25rem !important;
  color: var(--text-primary) !important;
  animation: fadeInUp 0.5s ease 0.1s both;
}

.hero-title .grad {
  background: linear-gradient(135deg, #818cf8 0%, #6366f1 35%, #a78bfa 70%, #c084fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 1.2rem;
  color: var(--text-secondary);
  line-height: 1.7;
  max-width: 580px;
  margin-bottom: 0.75rem;
  font-weight: 400;
  animation: fadeInUp 0.5s ease 0.2s both;
}

.hero-desc {
  font-size: 0.9rem;
  color: var(--text-muted);
  line-height: 1.7;
  max-width: 520px;
  margin-bottom: 2rem;
  animation: fadeInUp 0.5s ease 0.3s both;
}

.hero-buttons {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  animation: fadeInUp 0.5s ease 0.4s both;
}

.hero-btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #6366f1, #7c3aed);
  color: #fff;
  font-weight: 600;
  font-size: 0.9rem;
  padding: 11px 22px;
  border-radius: var(--radius-md);
  border: none;
  cursor: pointer;
  text-decoration: none;
  box-shadow: 0 4px 20px rgba(99,102,241,0.4);
  transition: all 0.2s ease;
  letter-spacing: -0.01em;
}

.hero-btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 28px rgba(99,102,241,0.55);
  background: linear-gradient(135deg, #5457e8, #6d28d9);
}

.hero-btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-surface2);
  color: var(--text-primary);
  font-weight: 600;
  font-size: 0.9rem;
  padding: 11px 22px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-soft);
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s ease;
  letter-spacing: -0.01em;
}

.hero-btn-secondary:hover {
  background: var(--bg-surface3);
  border-color: var(--border);
  transform: translateY(-1px);
}

/* JSON Preview Card */
.json-preview-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-lg);
  padding: 1.25rem 1.5rem;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.78rem;
  line-height: 1.8;
  box-shadow: var(--shadow-lg), var(--shadow-glow);
  animation: fadeInRight 0.6s ease 0.2s both;
  overflow: hidden;
  position: relative;
}

.json-preview-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, #6366f1, #a78bfa, #c084fc);
}

.json-preview-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-soft);
}

.json-dot { width: 10px; height: 10px; border-radius: 50%; }
.json-dot.red   { background: #ff5f57; }
.json-dot.amber { background: #febc2e; }
.json-dot.green { background: #28c840; }

.json-preview-title {
  font-family: 'Inter', sans-serif;
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-left: auto;
  font-weight: 500;
}

.jk { color: #7dd3fc; }   /* key */
.jv { color: #86efac; }   /* string value */
.jn { color: #fbbf24; }   /* number */
.jb { color: #f472b6; }   /* boolean/null */
.jp { color: var(--text-muted); } /* punctuation */

/* ═══════════════════════════════════════════════════
   STATS ROW
═══════════════════════════════════════════════════ */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin: 1.5rem 0 2rem;
  animation: fadeInUp 0.4s ease 0.1s both;
}

.stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  padding: 1.1rem 1.25rem;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: var(--border);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stat-icon {
  width: 38px; height: 38px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}

.stat-icon.indigo { background: var(--indigo-dim); }
.stat-icon.green  { background: var(--green-dim); }
.stat-icon.amber  { background: var(--amber-dim); }
.stat-icon.blue   { background: rgba(59,130,246,0.12); }

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
  letter-spacing: -0.03em;
}

.stat-label {
  font-size: 0.78rem;
  color: var(--text-muted);
  margin-top: 2px;
  font-weight: 500;
}

/* ═══════════════════════════════════════════════════
   DOCUMENT TYPE CARD GRID
═══════════════════════════════════════════════════ */
.doc-type-section {
  margin-bottom: 1.75rem;
}

.section-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 0.75rem;
}

.doc-type-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.6rem;
}

.doc-type-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  padding: 0.9rem 0.75rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.18s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-decoration: none;
}

.doc-type-card:hover {
  border-color: rgba(99,102,241,0.4);
  background: var(--bg-surface2);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(99,102,241,0.15);
}

.doc-type-card.active {
  border-color: var(--indigo) !important;
  background: var(--indigo-dim) !important;
  box-shadow: 0 0 0 1px var(--indigo), 0 4px 20px rgba(99,102,241,0.25);
}

.doc-type-icon {
  font-size: 1.4rem;
  line-height: 1;
}

.doc-type-name {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-secondary);
  line-height: 1.2;
}

.doc-type-card.active .doc-type-name {
  color: #a5b4fc;
}

/* ═══════════════════════════════════════════════════
   PANEL CARDS (workspace panels)
═══════════════════════════════════════════════════ */
.panel-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-lg);
  overflow: hidden;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-soft);
  background: var(--bg-surface2);
}

.panel-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 100px;
  background: var(--indigo-dim);
  color: #a5b4fc;
  border: 1px solid rgba(99,102,241,0.25);
}

.panel-body {
  padding: 1.25rem;
}

/* ═══════════════════════════════════════════════════
   SECTION HEADERS
═══════════════════════════════════════════════════ */
.workspace-header {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

.workspace-header::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-soft);
}

/* ═══════════════════════════════════════════════════
   BUTTONS — PREMIUM OVERRIDES
═══════════════════════════════════════════════════ */
.stButton > button {
  font-family: 'Inter', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.875rem !important;
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--border-soft) !important;
  padding: 0.55rem 1.2rem !important;
  transition: all 0.18s ease !important;
  letter-spacing: -0.01em !important;
  background: var(--bg-surface2) !important;
  color: var(--text-primary) !important;
}

.stButton > button:hover {
  border-color: var(--border) !important;
  background: var(--bg-surface3) !important;
  transform: translateY(-1px) !important;
  box-shadow: var(--shadow-sm) !important;
}

.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #6366f1, #7c3aed) !important;
  border-color: transparent !important;
  color: #fff !important;
  box-shadow: 0 4px 14px rgba(99,102,241,0.4) !important;
}

.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #5457e8, #6d28d9) !important;
  box-shadow: 0 6px 20px rgba(99,102,241,0.55) !important;
  transform: translateY(-2px) !important;
}

/* Download buttons */
.stDownloadButton > button {
  font-family: 'Inter', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.8rem !important;
  border-radius: var(--radius-sm) !important;
  padding: 0.45rem 0.9rem !important;
  background: var(--bg-surface2) !important;
  border: 1px solid var(--border-soft) !important;
  color: var(--text-secondary) !important;
  transition: all 0.15s ease !important;
}

.stDownloadButton > button:hover {
  background: var(--bg-surface3) !important;
  border-color: var(--border) !important;
  color: var(--text-primary) !important;
  transform: translateY(-1px) !important;
}

/* ═══════════════════════════════════════════════════
   INPUTS & TEXTAREAS
═══════════════════════════════════════════════════ */
.stTextArea textarea {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.83rem !important;
  background: var(--bg-surface2) !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-md) !important;
  color: var(--text-primary) !important;
  resize: vertical !important;
  line-height: 1.7 !important;
  transition: border-color 0.15s ease !important;
}

.stTextArea textarea:focus {
  border-color: var(--indigo) !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}

.stTextInput input {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.875rem !important;
  background: var(--bg-surface2) !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-md) !important;
  color: var(--text-primary) !important;
  transition: border-color 0.15s ease !important;
}

.stTextInput input:focus {
  border-color: var(--indigo) !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}

.stSelectbox > div > div {
  background: var(--bg-surface2) !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-md) !important;
  color: var(--text-primary) !important;
}

/* ═══════════════════════════════════════════════════
   FILE UPLOADER
═══════════════════════════════════════════════════ */
.stFileUploader {
  border-radius: var(--radius-md) !important;
}

[data-testid="stFileUploader"] > div {
  background: var(--bg-surface2) !important;
  border: 2px dashed var(--border-soft) !important;
  border-radius: var(--radius-md) !important;
  transition: all 0.2s ease !important;
}

[data-testid="stFileUploader"] > div:hover {
  border-color: rgba(99,102,241,0.5) !important;
  background: var(--indigo-dim) !important;
}

/* ═══════════════════════════════════════════════════
   TABS — STYLED PILLS
═══════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
  background: var(--bg-surface) !important;
  border-radius: var(--radius-md) !important;
  padding: 4px !important;
  gap: 2px !important;
  border: 1px solid var(--border-soft) !important;
  width: fit-content !important;
}

.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-secondary) !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.85rem !important;
  padding: 7px 18px !important;
  border: none !important;
  transition: all 0.15s ease !important;
}

.stTabs [data-baseweb="tab"]:hover {
  color: var(--text-primary) !important;
  background: var(--bg-surface2) !important;
}

.stTabs [aria-selected="true"] {
  background: var(--indigo) !important;
  color: #fff !important;
  box-shadow: 0 2px 8px rgba(99,102,241,0.4) !important;
}

.stTabs [data-baseweb="tab-highlight"] {
  display: none !important;
}

.stTabs [data-baseweb="tab-border"] {
  display: none !important;
}

/* ═══════════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
  background: var(--bg-surface) !important;
  border-right: 1px solid var(--border-soft) !important;
}

[data-testid="stSidebar"] > div {
  background: var(--bg-surface) !important;
  padding-top: 1.5rem !important;
}

.sidebar-section {
  background: var(--bg-surface2);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  padding: 1rem;
  margin-bottom: 1rem;
}

.sidebar-section-title {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg-surface3);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  margin-bottom: 6px;
  font-size: 0.78rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.history-item:hover {
  border-color: var(--border);
  color: var(--text-primary);
}

/* Toggle */
.stToggle label {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.875rem !important;
  color: var(--text-secondary) !important;
}

/* ═══════════════════════════════════════════════════
   PROGRESS STEPS
═══════════════════════════════════════════════════ */
.progress-steps {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 1.25rem 1.5rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-lg);
  margin-bottom: 1.5rem;
  overflow: hidden;
  animation: fadeIn 0.4s ease;
}

.progress-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex: 1;
  position: relative;
}

.progress-step:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 16px;
  left: 60%;
  width: 80%;
  height: 1px;
  background: var(--border-soft);
}

.progress-step.done:not(:last-child)::after {
  background: var(--indigo);
}

.step-dot {
  width: 32px; height: 32px;
  border-radius: 50%;
  border: 2px solid var(--border-soft);
  background: var(--bg-surface2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
  position: relative;
  z-index: 1;
  transition: all 0.3s ease;
}

.progress-step.done .step-dot {
  background: var(--indigo);
  border-color: var(--indigo);
  color: #fff;
  box-shadow: 0 0 12px var(--indigo-glow);
}

.progress-step.active .step-dot {
  border-color: var(--indigo);
  color: var(--indigo);
  animation: pulse 1.5s infinite;
}

.step-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-muted);
  text-align: center;
  letter-spacing: 0.02em;
}

.progress-step.done .step-label {
  color: #a5b4fc;
}

/* ═══════════════════════════════════════════════════
   SUCCESS / STATUS BANNERS
═══════════════════════════════════════════════════ */
.success-banner {
  background: var(--green-dim);
  border: 1px solid rgba(34,197,94,0.3);
  border-left: 3px solid var(--green);
  border-radius: var(--radius-md);
  padding: 0.9rem 1.2rem;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 1.25rem;
  animation: slideInLeft 0.3s ease;
}

.success-banner .banner-icon { font-size: 1.1rem; }
.success-banner .banner-text {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--green);
}
.success-banner .banner-sub {
  font-size: 0.78rem;
  color: rgba(34,197,94,0.7);
  margin-top: 1px;
}

.warn-banner {
  background: var(--amber-dim);
  border: 1px solid rgba(245,158,11,0.3);
  border-left: 3px solid var(--amber);
  border-radius: var(--radius-md);
  padding: 0.9rem 1.2rem;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 1.25rem;
  animation: slideInLeft 0.3s ease;
}

.warn-banner .banner-icon { font-size: 1.1rem; }
.warn-banner .banner-text {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--amber);
}

/* ═══════════════════════════════════════════════════
   VALIDATION BADGE
═══════════════════════════════════════════════════ */
.validation-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 100px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.validation-badge.valid {
  background: var(--green-dim);
  color: var(--green);
  border: 1px solid rgba(34,197,94,0.3);
}

.validation-badge.warning {
  background: var(--amber-dim);
  color: var(--amber);
  border: 1px solid rgba(245,158,11,0.3);
}

/* ═══════════════════════════════════════════════════
   EXTRACTED FIELD CARDS
═══════════════════════════════════════════════════ */
.field-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 0.7rem;
  margin-bottom: 1.5rem;
  animation: fadeInUp 0.4s ease;
}

.field-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  padding: 0.9rem 1rem;
  transition: all 0.18s ease;
}

.field-card:hover {
  border-color: var(--border);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.field-card-label {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 5px;
}

.field-card-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  word-break: break-word;
  line-height: 1.4;
}

.field-card-value.empty {
  color: var(--text-muted);
  font-style: italic;
  font-weight: 400;
}

/* ═══════════════════════════════════════════════════
   RESULT METRICS ROW
═══════════════════════════════════════════════════ */
.result-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin-bottom: 1.25rem;
  animation: fadeInUp 0.35s ease;
}

.result-metric-card {
  background: var(--bg-surface2);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  padding: 0.85rem 1rem;
  text-align: center;
}

.result-metric-val {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.result-metric-lbl {
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--text-muted);
  margin-top: 2px;
}

/* ═══════════════════════════════════════════════════
   EMPTY STATE
═══════════════════════════════════════════════════ */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3.5rem 2rem;
  text-align: center;
  color: var(--text-muted);
  border: 2px dashed var(--border-soft);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  animation: fadeIn 0.4s ease;
}

.empty-state-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
  filter: grayscale(0.3);
}

.empty-state-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
  letter-spacing: -0.01em;
}

.empty-state-desc {
  font-size: 0.83rem;
  color: var(--text-muted);
  max-width: 280px;
  line-height: 1.6;
}

/* ═══════════════════════════════════════════════════
   COUNTER BADGES
═══════════════════════════════════════════════════ */
.counter-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}

/* ═══════════════════════════════════════════════════
   FORMAT TAGS
═══════════════════════════════════════════════════ */
.format-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.format-tag {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--bg-surface3);
  border: 1px solid var(--border-soft);
  color: var(--text-muted);
  letter-spacing: 0.04em;
}

/* ═══════════════════════════════════════════════════
   FOOTER
═══════════════════════════════════════════════════ */
.genie-footer {
  margin-top: 3rem;
  padding: 2rem 0;
  border-top: 1px solid var(--border-soft);
  text-align: center;
}

.footer-powered {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.footer-tech {
  font-size: 0.78rem;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
}

.footer-tech span.dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--indigo);
  display: inline-block;
}

.footer-links {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
  margin-bottom: 1rem;
}

.footer-link {
  font-size: 0.78rem;
  color: var(--text-muted);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.15s ease;
}

.footer-link:hover {
  color: var(--text-secondary);
}

.footer-credit {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.footer-credit span.heart {
  color: #f43f5e;
}

.footer-credit span.name {
  color: var(--text-secondary);
  font-weight: 600;
}

/* ═══════════════════════════════════════════════════
   DATAFRAME OVERRIDES
═══════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {
  border-radius: var(--radius-md) !important;
  overflow: hidden !important;
  border: 1px solid var(--border-soft) !important;
}

/* ═══════════════════════════════════════════════════
   JSON VIEWER
═══════════════════════════════════════════════════ */
.stJson {
  background: var(--bg-surface2) !important;
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--border-soft) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.8rem !important;
}

/* Code blocks */
.stCodeBlock pre, .stCode pre {
  background: var(--bg-surface2) !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-md) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.8rem !important;
}

/* ═══════════════════════════════════════════════════
   CHAT MESSAGES
═══════════════════════════════════════════════════ */
[data-testid="stChatMessage"] {
  background: var(--bg-surface2) !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-md) !important;
  padding: 0.75rem 1rem !important;
  margin-bottom: 0.5rem !important;
}

[data-testid="stChatInput"] {
  border-radius: var(--radius-md) !important;
  background: var(--bg-surface2) !important;
  border: 1px solid var(--border-soft) !important;
}

/* ═══════════════════════════════════════════════════
   PROGRESS BAR
═══════════════════════════════════════════════════ */
.stProgress > div > div > div > div {
  background: linear-gradient(90deg, #6366f1, #a78bfa) !important;
  border-radius: 100px !important;
}

/* ═══════════════════════════════════════════════════
   EXPANDER
═══════════════════════════════════════════════════ */
.streamlit-expanderHeader {
  background: var(--bg-surface2) !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-md) !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.875rem !important;
  color: var(--text-secondary) !important;
  transition: all 0.15s ease !important;
}

.streamlit-expanderHeader:hover {
  border-color: var(--border) !important;
  color: var(--text-primary) !important;
}

.streamlit-expanderContent {
  border: 1px solid var(--border-soft) !important;
  border-top: none !important;
  border-radius: 0 0 var(--radius-md) var(--radius-md) !important;
  background: var(--bg-surface) !important;
}

/* ═══════════════════════════════════════════════════
   ALERTS (info, warning, error, success)
═══════════════════════════════════════════════════ */
[data-testid="stAlert"] {
  border-radius: var(--radius-md) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.875rem !important;
}

/* ═══════════════════════════════════════════════════
   DIVIDER
═══════════════════════════════════════════════════ */
hr {
  border: none !important;
  border-top: 1px solid var(--border-soft) !important;
  margin: 1.25rem 0 !important;
}

/* ═══════════════════════════════════════════════════
   LABEL OVERRIDES
═══════════════════════════════════════════════════ */
label, .stLabel, [data-testid="stWidgetLabel"] {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.8rem !important;
  font-weight: 600 !important;
  color: var(--text-secondary) !important;
  letter-spacing: 0.01em !important;
}

/* ═══════════════════════════════════════════════════
   CAPTION & INFO
═══════════════════════════════════════════════════ */
.stCaption, [data-testid="stCaptionContainer"] {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.78rem !important;
  color: var(--text-muted) !important;
}

/* ═══════════════════════════════════════════════════
   KEYFRAME ANIMATIONS
═══════════════════════════════════════════════════ */
@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-8px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes fadeInRight {
  from { opacity: 0; transform: translateX(16px); }
  to   { opacity: 1; transform: translateX(0); }
}

@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-10px); }
  to   { opacity: 1; transform: translateX(0); }
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(99,102,241,0.4); }
  50%       { box-shadow: 0 0 0 6px rgba(99,102,241,0); }
}

@keyframes shimmer {
  0%   { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}

/* ═══════════════════════════════════════════════════
   SCROLLBAR
═══════════════════════════════════════════════════ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-surface); }
::-webkit-scrollbar-thumb {
  background: var(--bg-surface3);
  border-radius: 100px;
}
::-webkit-scrollbar-thumb:hover { background: var(--border); }

/* ═══════════════════════════════════════════════════
   SPINNER
═══════════════════════════════════════════════════ */
[data-testid="stSpinner"] {
  color: var(--indigo) !important;
}

/* ═══════════════════════════════════════════════════
   RADIO
═══════════════════════════════════════════════════ */
.stRadio label {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.875rem !important;
  color: var(--text-secondary) !important;
}

/* Checkbox */
.stCheckbox label {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.85rem !important;
  color: var(--text-secondary) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Navigation Bar ──────────────────────────────────────────────────────────────
st.markdown("""
<nav class="genie-nav">
  <div class="genie-nav-logo">
    <span class="emoji">🧞</span>
    <span class="logo-text">JSON Genie</span>
  </div>
  <div class="genie-nav-links">
    <span class="genie-nav-link">Home</span>
    <span class="genie-nav-link">Examples</span>
    <span class="genie-nav-link">Documentation</span>
    <a href="https://github.com/Anubhvtripathi/json-genie-text-to-structured-data" target="_blank" class="genie-nav-link">GitHub</a>
    <span class="genie-nav-link">About</span>
  </div>
  <div class="genie-nav-actions">
    <div class="nav-icon-btn" title="Toggle Theme">🌙</div>
    <div class="nav-icon-btn" title="Settings">⚙️</div>
    <div class="nav-icon-btn" title="Profile">👤</div>
  </div>
</nav>
""", unsafe_allow_html=True)

# ── Sidebar Settings ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:1.25rem;">
      <span style="font-size:1.3rem;">🧞</span>
      <span style="font-size:1rem;font-weight:700;color:#e2e8f0;letter-spacing:-0.02em;">JSON Genie</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Extraction Mode ──
    st.markdown('<div class="sidebar-section-title">⚡ Extraction Engine</div>', unsafe_allow_html=True)
    use_llm = st.toggle(
        "Use Groq AI (Llama-3.3)",
        value=False,
        help="Falls back to Rule-based extraction if key is missing.",
    )

    target_language = st.selectbox(
        "🌍 Output Language",
        ["English", "Spanish", "French", "German", "Hindi", "Japanese", "Chinese", "Arabic"],
        index=0,
        help="Language for extracted data values (AI only)."
    )

    st.markdown("---")

    # ── Schema Mode (only for custom) ──
    document_type = st.session_state.get("doc_type_card", "Invoice")
    schema_mode = "Visual"
    if document_type == "Custom Schema":
        st.markdown('<div class="sidebar-section-title">🛠️ Schema Builder</div>', unsafe_allow_html=True)
        schema_mode = st.radio("Mode", ["Visual Builder", "Raw JSON Schema"], horizontal=True)

    st.markdown("---")

    # ── Sample Loader ──
    st.markdown('<div class="sidebar-section-title">📋 Load Sample</div>', unsafe_allow_html=True)
    if document_type == "Invoice":
        relevant_samples = ["Invoice", "Messy Missing Fields"]
    elif document_type == "Email":
        relevant_samples = ["Email"]
    elif document_type == "Job Post":
        relevant_samples = ["Job Post"]
    else:
        relevant_samples = list(SAMPLE_TEXTS.keys())

    sample_key = st.selectbox("Sample", relevant_samples, label_visibility="collapsed")
    if st.button("📂 Load Sample Text", use_container_width=True):
        st.session_state["raw_input_text"] = SAMPLE_TEXTS.get(sample_key, "")
        st.toast(f"✅ Loaded '{sample_key}' sample", icon="📋")

    st.markdown("---")

    # ── Session History ──
    st.markdown('<div class="sidebar-section-title">🕐 Session History</div>', unsafe_allow_html=True)
    if not st.session_state["extraction_history"]:
        st.markdown('<div style="font-size:0.78rem;color:#64748b;padding:8px 0;">No extractions yet this session.</div>', unsafe_allow_html=True)
    else:
        for idx, item in enumerate(reversed(st.session_state["extraction_history"])):
            status_emoji = "✅" if item["valid"] else "⚠️"
            label = f"{status_emoji} {item['time']} · {item['doc_type']}"
            if st.button(label, key=f"hist_{idx}", use_container_width=True):
                st.session_state["raw_input_text"] = item["original_text"]
                st.toast(f"Reloaded {item['time']} entry")
        if st.button("🗑️ Clear History", type="secondary", use_container_width=True):
            st.session_state["extraction_history"] = []
            st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.75rem;color:#64748b;">🔗 <a href="https://github.com/Anubhvtripathi/json-genie-text-to-structured-data" style="color:#6366f1;text-decoration:none;" target="_blank">GitHub Repository</a></div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div style="font-size:0.72rem;color:#475569;margin-top:6px;">v1.0.0 · Built with Streamlit + Groq</div>',
        unsafe_allow_html=True
    )

# ── Hero Section ───────────────────────────────────────────────────────────────
hero_left, hero_right = st.columns([1.15, 0.85], gap="large")

with hero_left:
    st.markdown("""
    <div class="hero-section">
      <div class="hero-badge">✨ Powered by Groq &amp; Llama-3.3</div>
      <h1 class="hero-title">
        Transform text into<br><span class="grad">structured JSON</span>
      </h1>
      <p class="hero-subtitle">
        Extract validated, production-ready JSON from invoices, emails, resumes, contracts, and custom documents using AI.
      </p>
      <p class="hero-desc">
        Paste any unstructured document — JSON Genie intelligently maps it to a typed schema in seconds, with full validation and export support.
      </p>
    </div>
    """, unsafe_allow_html=True)

with hero_right:
    st.markdown("""
    <div class="json-preview-card">
      <div class="json-preview-header">
        <div class="json-dot red"></div>
        <div class="json-dot amber"></div>
        <div class="json-dot green"></div>
        <span class="json-preview-title">invoice_extracted.json</span>
      </div>
      <div>
        <span class="jp">{</span><br>
        &nbsp;&nbsp;<span class="jk">"invoice_number"</span><span class="jp">:</span> <span class="jv">"INV-1048"</span><span class="jp">,</span><br>
        &nbsp;&nbsp;<span class="jk">"vendor_name"</span><span class="jp">:</span> <span class="jv">"Acme Supplies LLC"</span><span class="jp">,</span><br>
        &nbsp;&nbsp;<span class="jk">"customer_name"</span><span class="jp">:</span> <span class="jv">"Northstar Analytics"</span><span class="jp">,</span><br>
        &nbsp;&nbsp;<span class="jk">"total"</span><span class="jp">:</span> <span class="jn">345.60</span><span class="jp">,</span><br>
        &nbsp;&nbsp;<span class="jk">"currency"</span><span class="jp">:</span> <span class="jv">"USD"</span><span class="jp">,</span><br>
        &nbsp;&nbsp;<span class="jk">"line_items"</span><span class="jp">:</span> <span class="jp">[</span><br>
        &nbsp;&nbsp;&nbsp;&nbsp;<span class="jp">{</span> <span class="jk">"description"</span><span class="jp">:</span> <span class="jv">"Cloud storage plan"</span><span class="jp">,</span> <span class="jk">"amount"</span><span class="jp">:</span> <span class="jn">240.00</span> <span class="jp">}</span><br>
        &nbsp;&nbsp;<span class="jp">],</span><br>
        &nbsp;&nbsp;<span class="jk">"valid"</span><span class="jp">:</span> <span class="jb">true</span><br>
        <span class="jp">}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Stats Row ──────────────────────────────────────────────────────────────────
total_proc = st.session_state["total_processed"]
avg_ms = int(st.session_state["total_response_ms"] / total_proc) if total_proc > 0 else 0
api_status = "🟢 Online" if os.getenv("GROQ_API_KEY") else "🔴 No Key"
last_acc = "—" if st.session_state["last_valid"] is None else ("100%" if st.session_state["last_valid"] else "Partial")

st.markdown(f"""
<div class="stats-row">
  <div class="stat-card">
    <div class="stat-icon indigo">📄</div>
    <div>
      <div class="stat-value">{total_proc}</div>
      <div class="stat-label">Documents Processed</div>
    </div>
  </div>
  <div class="stat-card">
    <div class="stat-icon blue">⚡</div>
    <div>
      <div class="stat-value">{avg_ms}ms</div>
      <div class="stat-label">Avg Response Time</div>
    </div>
  </div>
  <div class="stat-card">
    <div class="stat-icon green">✅</div>
    <div>
      <div class="stat-value">{last_acc}</div>
      <div class="stat-label">Last Validation</div>
    </div>
  </div>
  <div class="stat-card">
    <div class="stat-icon amber">🔌</div>
    <div>
      <div class="stat-value" style="font-size:1rem;padding-top:4px;">{api_status}</div>
      <div class="stat-label">Groq API Status</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Document Type Card Grid ────────────────────────────────────────────────────
DOC_TYPE_CARDS = [
    ("📄", "Invoice"),
    ("📧", "Email"),
    ("👤", "Job Post"),
    ("🏥", "Medical"),
    ("📑", "Contract"),
    ("⚙️", "Custom Schema"),
]

st.markdown('<div class="section-label">Document Type</div>', unsafe_allow_html=True)

# Render cards as columns
card_cols = st.columns(len(DOC_TYPE_CARDS))
for i, (icon, label) in enumerate(DOC_TYPE_CARDS):
    with card_cols[i]:
        is_active = st.session_state["doc_type_card"] == label
        card_class = "doc-type-card active" if is_active else "doc-type-card"
        st.markdown(f"""
        <div class="{card_class}" id="doc-card-{i}">
          <div class="doc-type-icon">{icon}</div>
          <div class="doc-type-name">{label}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(label, key=f"doctype_{i}", help=f"Select {label}", use_container_width=True):
            st.session_state["doc_type_card"] = label
            st.rerun()

# Sync document_type from card selection
document_type = st.session_state["doc_type_card"]
# For schema types that map to DOCUMENT_MODELS
_MODEL_KEY_MAP = {
    "Invoice": "Invoice",
    "Email": "Email",
    "Job Post": "Job Post",
    "Medical": "Invoice",      # fallback to Invoice schema
    "Contract": "Invoice",     # fallback to Invoice schema
    "Custom Schema": None,
}

st.markdown("<br>", unsafe_allow_html=True)

# ── Dynamic Model & Custom Schema Resolution ───────────────────────────────────
model = None
schema_error = None

if document_type == "Custom Schema":
    if schema_mode == "Visual Builder":
        custom_schema_dict = render_schema_builder()
        try:
            model = build_model_from_json_schema("CustomDocument", custom_schema_dict)
            st.success("✅ Visual schema is valid and ready.")
        except Exception as exc:
            model = None
            schema_error = f"Builder Error: {exc}"
    else:
        st.markdown('<div class="workspace-header">🛠️ Raw JSON Schema Editor</div>', unsafe_allow_html=True)
        raw_schema = st.text_area(
            "JSON Schema",
            value=json.dumps(USER_SCHEMA_EXAMPLE, indent=2),
            height=250,
            label_visibility="collapsed",
        )
        try:
            custom_schema_dict = json.loads(raw_schema)
            model = build_model_from_json_schema("CustomDocument", custom_schema_dict)
            st.success("✅ Raw JSON schema parsed successfully.")
        except Exception as exc:
            model = None
            schema_error = f"Parse Error: {exc}"
else:
    _mk = _MODEL_KEY_MAP.get(document_type)
    if _mk and _mk in DOCUMENT_MODELS:
        model = DOCUMENT_MODELS[_mk]
    else:
        model = DOCUMENT_MODELS["Invoice"]

# ── Main Tabs ──────────────────────────────────────────────────────────────────
st.markdown('<div class="workspace-header">Workspace</div>', unsafe_allow_html=True)
tab_single, tab_batch, tab_chat = st.tabs(["📄 Single Document", "📁 Batch Processing", "💬 Genie Chat"])

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — SINGLE DOCUMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab_single:
    left_col, right_col = st.columns([1, 1], gap="medium")

    # ── LEFT: Input Panel ──────────────────────────────────────────────────────
    with left_col:
        st.markdown("""
        <div class="panel-header" style="border-radius:12px 12px 0 0;margin-bottom:0;">
          <span class="panel-title">📥 Input Document</span>
          <span class="panel-badge">Editor</span>
        </div>
        """, unsafe_allow_html=True)

        # File upload
        uploaded_file = st.file_uploader(
            "Drag & drop or click to upload",
            type=["pdf", "docx", "txt", "csv", "json"],
            key="single_file_uploader",
            help="Supported: PDF, DOCX, TXT, CSV, JSON",
        )

        if uploaded_file is not None:
            file_key = f"read_{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get("last_read_file") != file_key:
                with st.spinner("Extracting text from file…"):
                    try:
                        file_bytes = uploaded_file.read()
                        extracted = extract_text_from_file(file_bytes, uploaded_file.name)
                        st.session_state["raw_input_text"] = extracted
                        st.session_state["last_read_file"] = file_key
                        st.toast(f"📄 Extracted content from {uploaded_file.name}")
                    except Exception as e:
                        st.error(f"Error reading file: {e}")

        # Supported formats display
        st.markdown("""
        <div class="format-tags" style="margin-bottom:10px;">
          <span class="format-tag">TXT</span>
          <span class="format-tag">PDF</span>
          <span class="format-tag">DOCX</span>
          <span class="format-tag">CSV</span>
          <span class="format-tag">JSON</span>
        </div>
        """, unsafe_allow_html=True)

        # Text input
        input_text = st.text_area(
            "Paste or edit document text:",
            value=st.session_state["raw_input_text"],
            height=280,
            key="input_text_area",
            placeholder="Paste unstructured text here — invoice, email, resume, contract…",
        )
        st.session_state["raw_input_text"] = input_text

        # Character & word counter
        char_count = len(input_text)
        word_count = len(input_text.split()) if input_text.strip() else 0
        st.markdown(
            f'<div class="counter-badge">📊 {char_count:,} chars · {word_count:,} words</div>',
            unsafe_allow_html=True
        )

        # Schema error notice
        if schema_error:
            st.error(f"⚠️ Schema Error: {schema_error}")

        # Action buttons
        btn_col1, btn_col2 = st.columns([2, 1])
        with btn_col1:
            extract_clicked = st.button(
                "✨ Generate JSON",
                type="primary",
                use_container_width=True,
                key="extract_btn",
            )
        with btn_col2:
            if st.button("🔄 Clear", use_container_width=True, key="clear_btn"):
                st.session_state["raw_input_text"] = ""
                st.rerun()

    # ── RIGHT: Output Panel ────────────────────────────────────────────────────
    with right_col:
        st.markdown("""
        <div class="panel-header" style="border-radius:12px 12px 0 0;margin-bottom:0;">
          <span class="panel-title">📤 Generated JSON</span>
          <span class="panel-badge">Output</span>
        </div>
        """, unsafe_allow_html=True)

        if extract_clicked:
            if not input_text.strip():
                st.warning("⚠️ Please provide some input text first.")
            elif model is None:
                st.error("❌ Fix schema errors before running extraction.")
            else:
                # ── Processing steps animation ──
                steps = [
                    ("📖", "Reading"),
                    ("🔍", "Extracting"),
                    ("⚙️", "Generating"),
                    ("🛡️", "Validating"),
                    ("✅", "Complete"),
                ]

                steps_html = '<div class="progress-steps">'
                for step_idx, (step_icon, step_label) in enumerate(steps):
                    steps_html += f"""
                    <div class="progress-step done">
                      <div class="step-dot">{step_icon}</div>
                      <div class="step-label">{step_label}</div>
                    </div>
                    """
                steps_html += "</div>"

                with st.spinner("Processing document…"):
                    start_time = datetime.now()
                    result: ExtractionResult = extract_structured_data(
                        text=input_text,
                        model=model,
                        document_type=document_type if document_type in DOCUMENT_MODELS else "Invoice",
                        prefer_llm=use_llm,
                        language=target_language
                    )
                    end_time = datetime.now()

                # Update stats
                elapsed_ms = int((end_time - start_time).total_seconds() * 1000)
                st.session_state["total_processed"] += 1
                st.session_state["total_response_ms"] += elapsed_ms
                st.session_state["last_valid"] = result.valid

                # Save to history
                st.session_state["extraction_history"].append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "doc_type": document_type,
                    "original_text": input_text,
                    "result": result.data,
                    "valid": result.valid
                })

                # Show progress steps
                st.markdown(steps_html, unsafe_allow_html=True)

                # Success / warning banner
                if result.valid:
                    st.markdown(f"""
                    <div class="success-banner">
                      <span class="banner-icon">🎉</span>
                      <div>
                        <div class="banner-text">Extraction Complete</div>
                        <div class="banner-sub">Schema validated · {elapsed_ms}ms · {document_type}</div>
                      </div>
                      <span class="validation-badge valid" style="margin-left:auto;">✓ Schema Validated</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="warn-banner">
                      <span class="banner-icon">⚠️</span>
                      <div>
                        <div class="banner-text">Extraction Complete with Warnings</div>
                      </div>
                      <span class="validation-badge warning" style="margin-left:auto;">⚠ Validation Warning</span>
                    </div>
                    """, unsafe_allow_html=True)

                # Completeness metrics
                total_fields = len(result.data)
                non_null_fields = sum(1 for v in result.data.values() if v not in (None, [], {}, ""))
                completeness_pct = int((non_null_fields / total_fields) * 100) if total_fields > 0 else 0
                method_used = "Groq AI" if "Groq" in result.extractor else "Rule-based"

                st.markdown(f"""
                <div class="result-metrics">
                  <div class="result-metric-card">
                    <div class="result-metric-val">{"✅ PASS" if result.valid else "⚠️ WARN"}</div>
                    <div class="result-metric-lbl">Validation</div>
                  </div>
                  <div class="result-metric-card">
                    <div class="result-metric-val">{completeness_pct}%</div>
                    <div class="result-metric-lbl">Completeness</div>
                  </div>
                  <div class="result-metric-card">
                    <div class="result-metric-val" style="font-size:0.9rem;">{method_used}</div>
                    <div class="result-metric-lbl">Engine</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # Extracted field cards (top-level scalar fields only)
                scalar_fields = {
                    k: v for k, v in result.data.items()
                    if not isinstance(v, (list, dict))
                }
                if scalar_fields:
                    cards_html = '<div class="field-cards-grid">'
                    for k, v in scalar_fields.items():
                        label = k.replace("_", " ").title()
                        if v is None or v == "":
                            val_html = f'<div class="field-card-value empty">—</div>'
                        else:
                            val_html = f'<div class="field-card-value">{v}</div>'
                        cards_html += f"""
                        <div class="field-card">
                          <div class="field-card-label">{label}</div>
                          {val_html}
                        </div>
                        """
                    cards_html += "</div>"
                    st.markdown(cards_html, unsafe_allow_html=True)

                # JSON output
                st.json(result.data)

                # Downloads
                try:
                    df = results_to_dataframe(result.data)
                    csv_bytes = dataframe_to_csv(df)
                    excel_bytes = dataframe_to_excel(df)
                except Exception as e:
                    df = None
                    st.error(f"Could not convert to table: {e}")

                dl_col1, dl_col2, dl_col3 = st.columns(3)
                with dl_col1:
                    st.download_button(
                        "⬇ JSON",
                        data=json.dumps(result.data, indent=2),
                        file_name=f"{document_type.lower().replace(' ', '_')}_extracted.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                with dl_col2:
                    if df is not None:
                        st.download_button(
                            "⬇ CSV",
                            data=csv_bytes,
                            file_name=f"{document_type.lower().replace(' ', '_')}_extracted.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                with dl_col3:
                    if df is not None:
                        st.download_button(
                            "⬇ Excel",
                            data=excel_bytes,
                            file_name=f"{document_type.lower().replace(' ', '_')}_extracted.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )

                # Validation errors table
                if result.errors:
                    with st.expander("⚠️ Schema Validation Details"):
                        st.dataframe(
                            validation_errors_to_rows(result.errors),
                            use_container_width=True,
                        )

                # Raw LLM output expander
                if result.raw_response:
                    with st.expander("🔍 Raw LLM Response"):
                        st.code(result.raw_response, language="json")

        else:
            # Empty state
            st.markdown("""
            <div class="empty-state">
              <div class="empty-state-icon">✨</div>
              <div class="empty-state-title">Ready to Generate</div>
              <div class="empty-state-desc">
                Paste a document or upload a file on the left, then click
                <strong>Generate JSON</strong> to extract structured data.
              </div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — BATCH PROCESSING
# ══════════════════════════════════════════════════════════════════════════════
with tab_batch:
    st.markdown("""
    <div style="padding:0.5rem 0 1.5rem;">
      <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;margin-bottom:0.4rem;">📁 Batch Document Processing</div>
      <div style="font-size:0.85rem;color:#64748b;line-height:1.6;">
        Upload multiple files — the app extracts structured data from each and compiles a unified table.
        Supports PDF, DOCX, TXT, CSV, and JSON.
      </div>
    </div>
    """, unsafe_allow_html=True)

    batch_files = st.file_uploader(
        "Upload multiple files",
        type=["pdf", "docx", "txt", "csv", "json"],
        accept_multiple_files=True,
        key="batch_files_uploader",
    )

    process_batch_clicked = st.button("✨ Run Batch Extraction", type="primary", use_container_width=False, key="batch_btn")

    if process_batch_clicked:
        if not batch_files:
            st.warning("⚠️ Please upload at least one file for batch processing.")
        elif model is None:
            st.error("❌ Fix schema configuration before running.")
        else:
            batch_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, file in enumerate(batch_files):
                status_text.markdown(
                    f'<div style="font-size:0.83rem;color:#94a3b8;">Processing <strong style="color:#e2e8f0;">{file.name}</strong> ({idx+1}/{len(batch_files)})…</div>',
                    unsafe_allow_html=True
                )
                try:
                    file_bytes = file.read()
                    file_text = extract_text_from_file(file_bytes, file.name)
                    res: ExtractionResult = extract_structured_data(
                        text=file_text,
                        model=model,
                        document_type=document_type if document_type in DOCUMENT_MODELS else "Invoice",
                        prefer_llm=use_llm,
                        language=target_language
                    )
                    record = {"filename": file.name, "valid": res.valid, **res.data}
                    batch_results.append(record)
                except Exception as exc:
                    st.error(f"Error processing {file.name}: {exc}")

                progress_bar.progress((idx + 1) / len(batch_files))

            status_text.markdown(
                '<div style="font-size:0.83rem;color:#22c55e;">🎉 Batch processing complete!</div>',
                unsafe_allow_html=True
            )

            if batch_results:
                st.markdown('<div class="workspace-header">📊 Combined Results</div>', unsafe_allow_html=True)

                try:
                    batch_df = results_to_dataframe(batch_results)
                    st.dataframe(batch_df, use_container_width=True)

                    csv_batch = dataframe_to_csv(batch_df)
                    excel_batch = dataframe_to_excel(batch_df)

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        st.download_button(
                            "⬇ Download Combined CSV",
                            data=csv_batch,
                            file_name=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                    with col_dl2:
                        st.download_button(
                            "⬇ Download Combined Excel",
                            data=excel_batch,
                            file_name=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                except Exception as err:
                    st.error(f"Error compiling batch results: {err}")

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — GENIE CHAT
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    st.markdown("""
    <div style="padding:0.5rem 0 1.25rem;">
      <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;margin-bottom:0.4rem;">💬 Genie Chat</div>
      <div style="font-size:0.85rem;color:#64748b;line-height:1.6;">
        Ask questions about your loaded document, schema validations, or extraction details.
        The AI responds in context of your active document only.
      </div>
    </div>
    """, unsafe_allow_html=True)

    current_doc = st.session_state.get("raw_input_text", "").strip()

    if current_doc:
        with st.expander("📄 Active Document Preview"):
            st.text(current_doc[:1000] + ("…" if len(current_doc) > 1000 else ""))
    else:
        st.info("💡 Upload a document or paste text in the **Single Document** tab first to enable contextual chat.")

    if st.session_state["chat_history"]:
        if st.button("🧹 Clear Chat", type="secondary"):
            st.session_state["chat_history"] = []
            st.rerun()

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Ask about the document…"):
        with st.chat_message("user"):
            st.write(prompt)
        st.session_state["chat_history"].append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                try:
                    api_key = st.secrets.get("GROQ_API_KEY")
                except Exception:
                    pass

            if not api_key:
                st.error("❌ Groq API key missing. Set GROQ_API_KEY in your .env or secrets.")
            else:
                with st.spinner("Genie is thinking…"):
                    try:
                        from groq import Groq
                        client = Groq(api_key=api_key)
                        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

                        system_prompt = (
                            "You are JSON Genie, a helpful AI document extraction assistant.\n"
                            "Answer questions about the document below or discuss schemas/extraction rules.\n"
                            "IMPORTANT: Only discuss topics related to the document, job extraction, invoices, emails, schemas, or data processing. "
                            "Politely decline unrelated questions and steer back to the document.\n\n"
                            f"Active Document:\n{current_doc if current_doc else '(No document loaded.)'}"
                        )

                        messages = [{"role": "system", "content": system_prompt}]
                        for m in st.session_state["chat_history"][-10:]:
                            messages.append({"role": m["role"], "content": m["content"]})

                        completion = client.chat.completions.create(
                            model=model_name,
                            messages=messages,
                            temperature=0.2,
                        )
                        response = completion.choices[0].message.content
                        st.write(response)
                        st.session_state["chat_history"].append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"Error calling Groq: {e}")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="genie-footer">
  <div class="footer-powered">
    <span class="footer-tech"><span class="dot"></span> Groq Cloud</span>
    <span class="footer-tech"><span class="dot"></span> Llama 3.3</span>
    <span class="footer-tech"><span class="dot"></span> Pydantic</span>
    <span class="footer-tech"><span class="dot"></span> Streamlit</span>
  </div>
  <div class="footer-links">
    <a href="https://github.com/Anubhvtripathi/json-genie-text-to-structured-data" target="_blank" class="footer-link">GitHub</a>
    <a href="#" class="footer-link">Documentation</a>
    <a href="#" class="footer-link">Privacy</a>
    <span class="footer-link" style="color:#475569;cursor:default;">v1.0.0</span>
  </div>
  <div class="footer-credit">
    Made with <span class="heart">❤️</span> by <span class="name">Anubhav Tripathi</span>
  </div>
</div>
""", unsafe_allow_html=True)
