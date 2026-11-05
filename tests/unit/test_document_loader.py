
from pathlib import Path

import pytest
from docx import Document
from reportlab.pdfgen import canvas

from backend.rag.document_loader import load_document


def test_load_txt_document(tmp_path: Path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text(
        "Production RAG TXT Test Document",
        encoding="utf-8",
    )

    text = load_document(file_path)

    assert "Production RAG TXT Test Document" in text


def test_load_pdf_document(tmp_path: Path):
    file_path = tmp_path / "sample.pdf"

    pdf = canvas.Canvas(str(file_path))
    pdf.drawString(72, 750, "Production RAG PDF Test Document")
    pdf.save()

    text = load_document(file_path)

    assert "Production RAG PDF Test Document" in text


def test_load_docx_document(tmp_path: Path):
    file_path = tmp_path / "sample.docx"

    document = Document()
    document.add_heading("Production RAG DOCX Test Document", level=1)
    document.save(file_path)

    text = load_document(file_path)

    assert "Production RAG DOCX Test Document" in text


def test_missing_document_raises_error(tmp_path: Path):
    file_path = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError):
        load_document(file_path)


def test_unsupported_document_format(tmp_path: Path):
    file_path = tmp_path / "sample.csv"
    file_path.write_text("sample,data", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        load_document(file_path)


def test_empty_txt_document_raises_error(tmp_path: Path):
    file_path = tmp_path / "empty.txt"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="No readable text"):
        load_document(file_path)
