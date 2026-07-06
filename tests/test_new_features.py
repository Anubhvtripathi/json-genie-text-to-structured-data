from __future__ import annotations

import io
import pandas as pd
from src.json_genie.file_reader import extract_text_from_file
from src.json_genie.utils import flatten_dict, results_to_dataframe, dataframe_to_csv, dataframe_to_excel


def test_file_reader_txt():
    content = b"Hello, this is a text file content."
    text = extract_text_from_file(content, "test.txt")
    assert text == "Hello, this is a text file content."


def test_flatten_dict():
    nested = {
        "name": "Acme",
        "details": {
            "founded": 2000,
            "location": "Austin"
        },
        "tags": ["cloud", "saas"]
    }
    flat = flatten_dict(nested)
    assert flat["name"] == "Acme"
    assert flat["details_founded"] == 2000
    assert flat["details_location"] == "Austin"
    assert flat["tags"] == "cloud, saas"


def test_results_to_dataframe():
    results = [
        {"name": "Invoice 1", "amount": 100.0},
        {"name": "Invoice 2", "amount": 250.0}
    ]
    df = results_to_dataframe(results)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["name", "amount"]


def test_export_formats():
    df = pd.DataFrame([{"col1": "val1", "col2": 123}])
    
    csv_bytes = dataframe_to_csv(df)
    assert isinstance(csv_bytes, bytes)
    assert b"col1,col2" in csv_bytes
    
    excel_bytes = dataframe_to_excel(df)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0
