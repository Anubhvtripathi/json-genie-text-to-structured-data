from __future__ import annotations

import io
from pypdf import PdfReader
from docx import Document

def extract_text_from_file(file_contents: bytes, filename: str) -> str:
    """
    Extracts text from file bytes based on the filename extension.
    Supports .txt, .pdf, and .docx.
    """
    ext = filename.lower().split(".")[-1]
    if ext == "pdf":
        try:
            pdf_file = io.BytesIO(file_contents)
            reader = PdfReader(pdf_file)
            text_parts = []
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
            return "\n".join(text_parts)
        except Exception as e:
            raise ValueError(f"Failed to read PDF file: {e}")
    elif ext == "docx":
        try:
            docx_file = io.BytesIO(file_contents)
            doc = Document(docx_file)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            raise ValueError(f"Failed to read DOCX file: {e}")
    elif ext in ("txt", "csv", "json", "xml", "html"):
        try:
            return file_contents.decode("utf-8", errors="ignore")
        except Exception as e:
            raise ValueError(f"Failed to decode text file: {e}")
    else:
        # Fallback to decode as text
        try:
            return file_contents.decode("utf-8", errors="ignore")
        except Exception:
            raise ValueError(f"Unsupported file format: .{ext}")
