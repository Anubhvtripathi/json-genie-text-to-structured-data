from src.json_genie.dynamic_schema import build_model_from_json_schema
from src.json_genie.extractors import extract_structured_data
from src.json_genie.sample_data import SAMPLE_TEXTS, USER_SCHEMA_EXAMPLE
from src.json_genie.schemas import EmailDocument, Invoice, JobPost


def test_invoice_extraction_validates():
    result = extract_structured_data(SAMPLE_TEXTS["Invoice"], Invoice, "Invoice")

    assert result.valid is True
    assert result.data["invoice_number"] == "INV-1048"
    assert result.data["total"] == 345.60
    assert len(result.data["line_items"]) == 2


def test_email_extraction_handles_actions():
    result = extract_structured_data(SAMPLE_TEXTS["Email"], EmailDocument, "Email")

    assert result.valid is True
    assert result.data["priority"] == "high"
    assert result.data["intent"] == "reschedule meeting"
    assert result.data["action_items"]


def test_job_post_extraction_validates():
    result = extract_structured_data(SAMPLE_TEXTS["Job Post"], JobPost, "Job Post")

    assert result.valid is True
    assert result.data["job_title"] == "Data Analyst"
    assert "Python" in result.data["required_skills"]
    assert result.data["experience_years"] == 3


def test_missing_invoice_fields_do_not_crash():
    result = extract_structured_data(SAMPLE_TEXTS["Messy Missing Fields"], Invoice, "Invoice")

    assert isinstance(result.data, dict)
    assert "invoice_number" in result.data
    assert result.data["invoice_number"] is None


def test_custom_schema_runtime_model():
    model = build_model_from_json_schema("SupportTicket", USER_SCHEMA_EXAMPLE)
    text = "customer_name: Maya Lee\nissue_summary: Cannot access dashboard\nurgency: high"

    result = extract_structured_data(text, model, "Custom Schema")

    assert result.valid is True
    assert result.data["customer_name"] == "Maya Lee"
    assert result.data["issue_summary"] == "Cannot access dashboard"
