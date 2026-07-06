# 🧞 JSON Genie: Text to Structured Data

JSON Genie is a Streamlit app that turns messy text from invoices, emails, job posts, or any user-defined document type into clean, schema-validated JSON.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://json-genie-text-to-structured-data-ntksiqtp7tbeyvsngyvjfu.streamlit.app/)

**🚀 Live Demo**: [https://json-genie-text-to-structured-data-ntksiqtp7tbeyvsngyvjfu.streamlit.app/](https://json-genie-text-to-structured-data-ntksiqtp7tbeyvsngyvjfu.streamlit.app/)

---

## Features

- 🧾 Extracts structured JSON from **invoices, emails, and job posts**
- ✅ Validates output with **Pydantic models**
- 🤖 Powered by **Groq (Llama 3)** when an API key is configured
- 🔁 Falls back to a **local rule-based extractor** when no API key is set
- 🧩 Supports a **runtime user-defined JSON schema**
- ⬇️ **Export extracted JSON** with one click
- Shows validation errors and partial JSON clearly

---

## Quick Start (Local)

### 1. Clone the repository

```bash
git clone https://github.com/Anubhvtripathi/json-genie-text-to-structured-data.git
cd json-genie-text-to-structured-data
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your Groq API key (optional but recommended)

Copy the example file and fill in your key:

```bash
copy .env.example .env   # Windows
cp .env.example .env     # macOS / Linux
```

Then edit `.env`:

```env
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

> Get a free Groq API key at https://console.groq.com

### 5. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## Run Tests

```bash
# Windows
$env:PYTHONPATH="."; .venv\Scripts\pytest

# macOS / Linux
PYTHONPATH=. pytest
```

All 5 tests should pass.

---

## Deploy to Streamlit Cloud (Free)

1. Push this project to a GitHub repository.
2. Go to [https://streamlit.io/cloud](https://streamlit.io/cloud) and sign in.
3. Click **"New app"** and connect your GitHub repository.
4. Set the **Main file path** to `app.py`.
5. Under **Advanced settings → Secrets**, add:

```toml
GROQ_API_KEY = "your_key_here"
GROQ_MODEL = "llama-3.3-70b-versatile"
```

6. Click **Deploy** — your app will be live in ~30 seconds!

> ⚠️ **Never commit your real `.env` file to GitHub.** It is already excluded via `.gitignore`.

---

## Project Structure

```
json-genie-text-to-structured-data/
├── app.py                          # Streamlit UI entrypoint
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── .streamlit/
│   └── secrets.toml.example        # Streamlit Cloud secrets template
├── src/
│   └── json_genie/
│       ├── dynamic_schema.py       # Runtime JSON schema → Pydantic model
│       ├── extractors.py           # Rule-based & Groq LLM extractors
│       ├── sample_data.py          # Built-in sample texts
│       ├── schemas.py              # Invoice, Email, JobPost Pydantic models
│       └── utils.py                # Validation error formatting
├── tests/
│   └── test_extractors.py          # Pytest test suite
└── examples/
    ├── invoice.txt
    ├── email.txt
    └── job_post.txt
```

---

## How It Works

1. **Paste** any unstructured text (invoice, email, job post, or custom).
2. **Select** a document type and optionally enable Groq LLM extraction.
3. **Click** "Extract JSON" — the app validates the output against a Pydantic schema.
4. **Download** the clean JSON or inspect any validation warnings.

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| [Streamlit](https://streamlit.io) | Web UI |
| [Pydantic v2](https://docs.pydantic.dev) | Schema validation |
| [Groq](https://groq.com) | LLM JSON extraction |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | Environment config |
| [pytest](https://pytest.org) | Testing |
