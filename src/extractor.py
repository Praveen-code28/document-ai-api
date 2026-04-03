from __future__ import annotations

import os
import zipfile
from xml.etree import ElementTree as ET

try:
    import pytesseract
except Exception:
    pytesseract = None  # type: ignore

try:
    from PIL import Image
except Exception:
    Image = None  # type: ignore

try:
    import pymupdf as fitz  # Preferred modern import
except Exception:
    try:
        import fitz  # type: ignore
    except Exception:
        fitz = None  # type: ignore

try:
    import docx  # type: ignore
except Exception:
    docx = None  # type: ignore


def _configure_tesseract() -> None:
    """Set optional tesseract executable path via env variable."""
    if pytesseract is None:
        return
    tesseract_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def extract_pdf(file_path: str) -> str:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not available for PDF extraction")
    text_parts: list[str] = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text_parts.append(page.get_text() or "")
    return "\n".join(text_parts)


def extract_docx(file_path: str) -> str:
    # Preferred path via python-docx; fallback uses XML parsing for robustness.
    if docx is not None:
        document = docx.Document(file_path)
        return "\n".join(para.text for para in document.paragraphs if para.text)

    text_parts: list[str] = []
    with zipfile.ZipFile(file_path, "r") as archive:
        xml_data = archive.read("word/document.xml")
        root = ET.fromstring(xml_data)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        for node in root.findall(".//w:t", namespace):
            if node.text and node.text.strip():
                text_parts.append(node.text.strip())
    return " ".join(text_parts)


def extract_image(file_path: str) -> str:
    if pytesseract is None or Image is None:
        return ""
    _configure_tesseract()
    try:
        with Image.open(file_path) as image:
            # Reduce OCR latency/memory for very large images.
            image = image.convert("L")
            image.thumbnail((1800, 1800))
            return pytesseract.image_to_string(image, config="--oem 1 --psm 6") or ""
    except Exception:
        return ""


def extract_text(file_path: str, file_type: str) -> str:
    normalized = (file_type or "").lower().strip()
    if normalized == "pdf":
        return extract_pdf(file_path)
    if normalized == "docx":
        return extract_docx(file_path)
    if normalized == "image":
        return extract_image(file_path)
    raise ValueError(f"Unsupported file type: {file_type}")