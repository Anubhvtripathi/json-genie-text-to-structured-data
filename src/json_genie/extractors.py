from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError


@dataclass
class ExtractionResult:
    data: dict[str, Any]
    valid: bool
    errors: list[dict[str, Any]]
    extractor: str
    raw_response: str | None = None


def extract_structured_data(
    text: str,
    model: type[BaseModel],
    document_type: str,
    prefer_llm: bool = False,
) -> ExtractionResult:
    if prefer_llm and _setting("GROQ_API_KEY"):
        try:
            return _extract_with_groq(text=text, model=model, document_type=document_type)
        except Exception as exc:
            fallback = _extract_with_rules(text=text, model=model, document_type=document_type)
            fallback.errors.append(
                {
                    "loc": ("llm",),
                    "msg": f"Groq extraction failed, used local fallback: {exc}",
                    "type": "llm_error",
                }
            )
            fallback.valid = False
            return fallback

    return _extract_with_rules(text=text, model=model, document_type=document_type)


def _extract_with_groq(
    text: str,
    model: type[BaseModel],
    document_type: str,
) -> ExtractionResult:
    from groq import Groq

    client = Groq(api_key=_setting("GROQ_API_KEY"))
    model_name = _setting("GROQ_MODEL", "llama-3.3-70b-versatile")
    schema = model.model_json_schema()

    prompt = (
        f"Extract a {document_type} from the text. Return only fields from the schema. "
        "Use null for unknown scalar values and [] for unknown list values. "
        "Do not invent facts. Return one valid JSON object only.\n\n"
        f"JSON Schema:\n{schema}\n\n"
        f"Text:\n{text}"
    )

    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You extract structured data and obey the provided schema."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    raw = completion.choices[0].message.content
    if not raw:
        raise ValueError("Model returned an empty response.")

    raw_data = _parse_json_object(raw)
    parsed = model.model_validate(raw_data)

    return ExtractionResult(
        data=parsed.model_dump(mode="json"),
        valid=True,
        errors=[],
        extractor="Groq JSON mode + Pydantic validation",
        raw_response=raw,
    )


def _parse_json_object(raw: str) -> dict[str, Any]:
    import json

    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise
        loaded = json.loads(match.group(0))

    if not isinstance(loaded, dict):
        raise ValueError("Model response was valid JSON but not an object.")
    return loaded


def _setting(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    try:
        import streamlit as st

        secret_value = st.secrets.get(name)
        if secret_value:
            return str(secret_value)
    except Exception:
        pass

    return default


def _extract_with_rules(text: str, model: type[BaseModel], document_type: str) -> ExtractionResult:
    if document_type == "Invoice":
        raw_data = _extract_invoice(text)
    elif document_type == "Email":
        raw_data = _extract_email(text)
    elif document_type == "Job Post":
        raw_data = _extract_job_post(text)
    else:
        raw_data = _extract_custom(text, model)

    return _validate(raw_data, model, extractor="Local demo extractor")


def _validate(raw_data: dict[str, Any], model: type[BaseModel], extractor: str) -> ExtractionResult:
    try:
        parsed = model.model_validate(raw_data)
        return ExtractionResult(
            data=parsed.model_dump(mode="json"),
            valid=True,
            errors=[],
            extractor=extractor,
        )
    except ValidationError as exc:
        partial = _best_effort_data(raw_data, model)
        return ExtractionResult(
            data=partial,
            valid=False,
            errors=exc.errors(),
            extractor=extractor,
        )


def _best_effort_data(raw_data: dict[str, Any], model: type[BaseModel]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for field_name, field in model.model_fields.items():
        if field_name in raw_data:
            data[field_name] = raw_data[field_name]
        elif field.default_factory is not None:
            data[field_name] = field.default_factory()
        elif field.default is not None:
            data[field_name] = field.default
        else:
            data[field_name] = None
    return data


def _extract_invoice(text: str) -> dict[str, Any]:
    return {
        "invoice_number": _invoice_number(text),
        "vendor_name": _first_nonempty_line(text),
        "customer_name": _first_match(text, r"(?:bill to|customer)\s*[:\-]\s*(.+)"),
        "invoice_date": _first_match(text, r"invoice date\s*[:\-]\s*(\d{4}-\d{2}-\d{2})"),
        "due_date": _first_match(text, r"due date\s*[:\-]\s*(\d{4}-\d{2}-\d{2})"),
        "line_items": _extract_line_items(text),
        "subtotal": _money_after(text, "subtotal"),
        "tax": _money_after(text, "tax"),
        "total": _money_after(text, "total due") or _money_after(text, "total"),
        "currency": "USD",
    }


def _extract_email(text: str) -> dict[str, Any]:
    lower = text.lower()
    action_items = []
    for marker in ["please ", "also ", "can you ", "could you "]:
        action_items.extend(_sentences_after_marker(text, marker))

    priority = "high" if any(word in lower for word in ["urgent", "asap", "immediately"]) else "normal"

    return {
        "sender": _first_match(text, r"from:\s*(.+)"),
        "recipient": _first_match(text, r"to:\s*(.+)"),
        "subject": _first_match(text, r"subject:\s*(.+)"),
        "date": _first_match(text, r"date:\s*(\d{4}-\d{2}-\d{2})"),
        "intent": _infer_email_intent(lower),
        "action_items": _dedupe(action_items),
        "priority": priority,
    }


def _extract_job_post(text: str) -> dict[str, Any]:
    first_line = _first_nonempty_line(text) or ""
    title, company = _split_title_company(first_line)
    skills = _skills_from_text(text)

    return {
        "job_title": title,
        "company": company,
        "location": _first_match(text, r"location:\s*(.+)"),
        "employment_type": _first_match(text, r"(?:employment|type):\s*(.+)"),
        "salary_range": _first_match(text, r"salary:\s*(.+)"),
        "required_skills": skills,
        "responsibilities": _bullet_lines_after(text, "responsibilities"),
        "experience_years": _experience_years(text),
    }


def _extract_custom(text: str, model: type[BaseModel]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for field_name, field in model.model_fields.items():
        pattern_name = field_name.replace("_", r"[\s_-]*")
        value = _first_match(text, rf"{pattern_name}\s*[:\-]\s*(.+)")
        if value is not None:
            data[field_name] = value
        elif "list[" in str(field.annotation).lower():
            data[field_name] = []
        elif lines:
            data[field_name] = None
    return data


def _first_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def _invoice_number(text: str) -> str | None:
    return (
        _first_match(text, r"invoice\s*#\s*([A-Z0-9\-]+)")
        or _first_match(text, r"invoice\s*(?:number|no\.?)\s*[:\-]\s*([A-Z0-9\-]+)")
    )


def _first_nonempty_line(text: str) -> str | None:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return None


def _money_after(text: str, label: str) -> float | None:
    pattern = rf"{re.escape(label)}\s*[:\-]?\s*\$?\s*([0-9,]+(?:\.\d+)?)"
    value = _first_match(text, pattern)
    if value is None:
        return None
    return float(value.replace(",", ""))


def _extract_line_items(text: str) -> list[dict[str, Any]]:
    items = []
    for line in text.splitlines():
        if not line.strip().startswith("-"):
            continue

        amount = _first_match(line, r"amount\s+([0-9]+(?:\.\d+)?)")
        unit_price = _first_match(line, r"unit price\s+([0-9]+(?:\.\d+)?)")
        quantity = _first_match(line, r"qty\s+([0-9]+(?:\.\d+)?)")
        description = line.strip("- ").split(",")[0].strip()

        items.append(
            {
                "description": description,
                "quantity": float(quantity or 1),
                "unit_price": float((unit_price or "0").replace(",", "")),
                "amount": float((amount or "0").replace(",", "")),
            }
        )
    return items


def _sentences_after_marker(text: str, marker: str) -> list[str]:
    results = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        idx = sentence.lower().find(marker)
        if idx >= 0:
            results.append(sentence[idx:].strip().rstrip("."))
    return results


def _infer_email_intent(lower_text: str) -> str:
    if "reschedule" in lower_text:
        return "reschedule meeting"
    if "invoice" in lower_text or "payment" in lower_text:
        return "billing"
    if "follow up" in lower_text:
        return "follow up"
    return "general request"


def _split_title_company(line: str) -> tuple[str | None, str | None]:
    if " - " in line:
        title, company = line.split(" - ", 1)
        return title.strip(), company.strip()
    return line.strip() or None, None


def _skills_from_text(text: str) -> list[str]:
    known_skills = [
        "Python",
        "SQL",
        "Tableau",
        "Power BI",
        "Excel",
        "Pandas",
        "Machine Learning",
        "Stakeholder Reporting",
    ]
    lower = text.lower()
    return [skill for skill in known_skills if skill.lower() in lower]


def _bullet_lines_after(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    collecting = False
    bullets = []
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith(heading.lower()):
            collecting = True
            continue
        if collecting and stripped.startswith("-"):
            bullets.append(stripped.strip("- "))
        elif collecting and stripped and not stripped.startswith("-"):
            break
    return bullets


def _experience_years(text: str) -> float | None:
    value = _first_match(text, r"(\d+(?:\.\d+)?)\+?\s*years")
    return float(value) if value else None


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    clean = []
    for value in values:
        normalized = value.lower()
        if normalized not in seen:
            seen.add(normalized)
            clean.append(value)
    return clean
