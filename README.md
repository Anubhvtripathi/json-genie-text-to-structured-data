# JSON Genie: Text to Structured Data

JSON Genie is a Streamlit app that turns messy text from invoices, emails, job posts, or a user-defined document type into schema-validated JSON.

It uses:

- Python
- Pydantic validation
- Streamlit UI
- Groq JSON mode when `GROQ_API_KEY` is configured
- A local rule-based demo extractor when no API key is available

## Features

- Extracts structured JSON from invoices, emails, and job posts
- Validates output with Pydantic models
- Handles missing or malformed fields without crashing
- Supports a runtime user-defined JSON schema
- Shows validation errors and partial JSON clearly
- Exports extracted JSON

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Optional, for LLM extraction:

```bash
copy .env.example .env
```

Then add your API key:

```text
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

For Streamlit Cloud, do not upload `.env`. Add these values in the app's **Secrets** settings instead:

```toml
GROQ_API_KEY = "your_key_here"
GROQ_MODEL = "llama-3.3-70b-versatile"
```

## Run

```bash
streamlit run app.py
```

## Test

```bash
pytest
```

## Deploy Online With Streamlit Cloud

1. Push this project to a GitHub repository.
2. Open Streamlit Cloud and create a new app from that repository.
3. Set the main file path to `app.py`.
4. Open the app settings and add your secrets:

```toml
GROQ_API_KEY = "your_key_here"
GROQ_MODEL = "llama-3.3-70b-versatile"
```

5. Deploy the app.

Never commit your real API key to GitHub.

## Project Structure

```text
app.py
src/json_genie/
  dynamic_schema.py
  extractors.py
  schemas.py
  sample_data.py
  utils.py
tests/
examples/
```

## Notes

The app gracefully falls back to a local demo extractor when no OpenAI API key is set. This makes the project easy to demonstrate in class or during development without paid API usage.
