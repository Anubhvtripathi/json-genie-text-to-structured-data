from __future__ import annotations

import json
from typing import Any
import pandas as pd
import io


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


def flatten_dict(d: dict[str, Any], parent_key: str = '', sep: str = '_') -> dict[str, Any]:
    """
    Flattens a nested dictionary for representation in flat tables (CSV/Excel).
    """
    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            if all(isinstance(i, str) for i in v):
                items.append((new_key, ", ".join(v)))
            else:
                items.append((new_key, json.dumps(v)))
        else:
            items.append((new_key, v))
    return dict(items)


def results_to_dataframe(results: list[dict[str, Any]] | dict[str, Any]) -> pd.DataFrame:
    """
    Converts a single result dict or a list of result dicts to a flat pandas DataFrame.
    """
    if isinstance(results, dict):
        results = [results]
    
    flat_results = [flatten_dict(r) for r in results]
    return pd.DataFrame(flat_results)


def dataframe_to_csv(df: pd.DataFrame) -> bytes:
    """
    Converts a DataFrame to CSV bytes.
    """
    return df.to_csv(index=False).encode("utf-8")


def dataframe_to_excel(df: pd.DataFrame) -> bytes:
    """
    Converts a DataFrame to Excel bytes using openpyxl.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Extracted Data")
    return output.getvalue()
