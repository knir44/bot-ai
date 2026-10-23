"""Turn an uploaded file into plain text. Validation already happened in core.security."""
from __future__ import annotations

import io

from app.core.security import ValidationError


def extract_text(data: bytes, ext: str) -> str:
    if ext == ".txt":
        return data.decode("utf-8-sig")
    if ext == ".pdf":
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:  # corrupt / encrypted PDFs
            raise ValidationError(f"Could not read PDF: {exc}")
        return "\n\n".join(pages)
    if ext == ".docx":
        from docx import Document

        try:
            doc = Document(io.BytesIO(data))
        except Exception as exc:
            raise ValidationError(f"Could not read DOCX: {exc}")
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    raise ValidationError(f"Unsupported file type {ext}")
