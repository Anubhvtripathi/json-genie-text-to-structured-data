from __future__ import annotations

from typing import Any


def validation_errors_to_rows(errors: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for error in errors:
        location = ".".join(str(part) for part in error.get("loc", []))
        rows.append(
            {
                "field": location or "document",
                "message": str(error.get("msg", "Invalid value")),
                "type": str(error.get("type", "validation_error")),
            }
        )
    return rows
