from __future__ import annotations

from datetime import date as Date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LineItem(BaseModel):
    description: str = Field(default="Unknown item")
    quantity: float = Field(default=1, ge=0)
    unit_price: float = Field(default=0, ge=0)
    amount: float = Field(default=0, ge=0)


class Invoice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    customer_name: Optional[str] = None
    invoice_date: Optional[Date] = None
    due_date: Optional[Date] = None
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = Field(default=None, ge=0)
    tax: Optional[float] = Field(default=None, ge=0)
    total: Optional[float] = Field(default=None, ge=0)
    currency: str = "USD"

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return (value or "USD").upper()


class EmailDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sender: Optional[str] = None
    recipient: Optional[str] = None
    subject: Optional[str] = None
    date: Optional[Date] = None
    intent: Optional[str] = None
    action_items: list[str] = Field(default_factory=list)
    priority: str = "normal"

    @field_validator("priority")
    @classmethod
    def normalize_priority(cls, value: str) -> str:
        normalized = (value or "normal").lower()
        return normalized if normalized in {"low", "normal", "high"} else "normal"


class JobPost(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    salary_range: Optional[str] = None
    required_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    experience_years: Optional[float] = Field(default=None, ge=0)


DOCUMENT_MODELS = {
    "Invoice": Invoice,
    "Email": EmailDocument,
    "Job Post": JobPost,
}
