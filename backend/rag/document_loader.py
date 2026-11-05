
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def load_document(file_path: str | Path) -> str:
    """
    Extract text from PDF, DOCX, or TXT files.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError("Document file does not exist")

    if not path.is_file():
        raise ValueError("Provided path is not a file")

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {extension}"
        )

    if extension == ".txt":
        text = path.read_text(encoding="utf-8-sig")

    elif extension == ".pdf":
        reader = PdfReader(str(path))

        if reader.is_encrypted:
            raise ValueError("Encrypted PDF files are not supported")

        extracted_pages = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                extracted_pages.append(page_text)

        text = "\n".join(extracted_pages)

    else:
        document = DocxDocument(str(path))
        text = "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

    cleaned_text = text.strip()

    if not cleaned_text:
        raise ValueError("No readable text found in document")

    return cleaned_text
