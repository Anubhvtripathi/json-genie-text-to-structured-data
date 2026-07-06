# JSON Genie: Text to Structured Data

JSON Genie is a Streamlit app that turns messy text from invoices, emails, job posts, or any user-defined document type into clean, schema-validated JSON.

Live demo:
https://json-genie-text-to-structured-data-ntksiqtp7tbeyvsngyvjfu.streamlit.app/

## Features

- Extracts structured JSON from invoices, emails, and job posts
- Validates output with Pydantic models
- Uses Groq Llama models when an API key is configured
- Falls back to a local rule-based extractor when no API key is set
- Supports runtime user-defined JSON schemas
- Supports file/text-based extraction workflows
- Exports extracted JSON
- Shows validation issues clearly without crashing

## Quick Start

### 1. Open the project folder

```powershell
cd C:\Users\HP\Documents\Codex\2026-07-05\json-genie-text-to-structured-data
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate it

```powershell
.venv\Scripts\activate
```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Add Groq API key

Create a `.env` file:

```text
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

The `.env` file is ignored by Git and should not be uploaded to GitHub.

### 6. Run the app

```powershell
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## Run Tests

```powershell
.venv\Scripts\python -m pytest
```

Expected result:

```text
9 passed
```

## Streamlit Cloud Deployment

1. Push this project to GitHub.
2. Go to https://streamlit.io/cloud.
3. Create a new app from the GitHub repository.
4. Set the main file path to `app.py`.
5. Add these secrets in Streamlit Cloud:

```toml
GROQ_API_KEY = "your_groq_api_key_here"
GROQ_MODEL = "llama-3.3-70b-versatile"
```

6. Deploy the app.

## Project Structure

```text
app.py
requirements.txt
.env.example
.streamlit/secrets.toml.example
src/json_genie/
  dynamic_schema.py
  extractors.py
  file_reader.py
  sample_data.py
  schema_builder.py
  schemas.py
  utils.py
tests/
examples/
```

## Tech Stack

- Python
- Streamlit
- Pydantic
- Groq API
- python-dotenv
- pytest
