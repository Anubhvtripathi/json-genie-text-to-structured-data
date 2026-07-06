SAMPLE_TEXTS = {
    "Invoice": """Acme Supplies LLC
Invoice # INV-1048
Bill to: Northstar Analytics
Invoice date: 2026-06-18
Due date: 2026-07-18

Items:
- Cloud storage plan, qty 2, unit price 120.00, amount 240.00
- Support package, qty 1, unit price 80.00, amount 80.00

Subtotal: $320.00
Tax: $25.60
Total Due: $345.60
""",
    "Email": """From: priya.shah@example.com
To: operations@example.com
Subject: Urgent: Reschedule onboarding call
Date: 2026-07-03

Hi team,
The new client cannot join tomorrow's onboarding call. Please move it to next Tuesday morning and send an updated invite. Also prepare the revised setup checklist before the call.

Thanks,
Priya
""",
    "Job Post": """Data Analyst - BrightMart Retail
Location: Austin, TX or Remote
Employment: Full-time
Salary: $85,000 - $105,000

We are looking for a Data Analyst with 3+ years of experience in SQL, Python, Tableau, and stakeholder reporting.

Responsibilities:
- Build weekly performance dashboards
- Analyze customer purchase behavior
- Present insights to product and marketing teams
""",
    "Messy Missing Fields": """Invoice
Vendor: QuickFix Services
Total maybe around 900 dollars.
The invoice number is not visible. Customer name missing. Date smudged.
""",
}


USER_SCHEMA_EXAMPLE = {
    "title": "SupportTicket",
    "type": "object",
    "required": ["customer_name", "issue_summary"],
    "properties": {
        "customer_name": {
            "type": "string",
            "description": "Name of the customer raising the issue",
        },
        "issue_summary": {
            "type": "string",
            "description": "Short summary of the customer problem",
        },
        "urgency": {
            "type": "string",
            "description": "low, normal, or high",
        },
        "requested_actions": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}
