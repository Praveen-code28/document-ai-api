from __future__ import annotations

import base64
import os
import tempfile

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from src.extractor import extract_text
from src.nlp import get_entities, get_sentiment, get_summary


load_dotenv()
EXPECTED_API_KEY = os.getenv("API_KEY", "")


class DocumentRequest(BaseModel):
    fileName: str
    fileType: str
    fileBase64: str


app = FastAPI(title="Document AI API", version="1.0.0")
ALLOWED_FILE_TYPES = {"pdf", "docx", "image"}


def _error_response(file_name: str) -> dict:
    return {
        "status": "error",
        "fileName": file_name,
        "summary": "",
        "entities": {
            "names": [],
            "dates": [],
            "organizations": [],
            "amounts": [],
        },
        "sentiment": "Neutral",
    }


def _suffix_for_type(file_type: str, file_name: str) -> str:
    if file_type == "pdf":
        return ".pdf"
    if file_type == "docx":
        return ".docx"
    _, ext = os.path.splitext(file_name or "")
    return ext if ext else ".png"


@app.post("/api/document-analyze")
def document_analyze(payload: DocumentRequest, x_api_key: str = Header(default="")):
    if not EXPECTED_API_KEY or x_api_key != EXPECTED_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    normalized_file_type = (payload.fileType or "").strip().lower()
    if normalized_file_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    temp_path = ""
    try:
        print(f"[INFO] Processing file type: {normalized_file_type}")

        try:
            binary_data = base64.b64decode(payload.fileBase64, validate=True)
        except Exception:
            return _error_response(payload.fileName)

        suffix = _suffix_for_type(normalized_file_type, payload.fileName)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(binary_data)
            temp_path = temp_file.name

        extracted_text = extract_text(temp_path, normalized_file_type)
        cleaned_text = " ".join((extracted_text or "").split())
        print(f"[INFO] Extracted text length: {len(cleaned_text)}")
        if len(cleaned_text) < 10:
            print("[ERROR] Extracted text is empty or too short for analysis")
            return _error_response(payload.fileName)

        summary = get_summary(cleaned_text)
        entities = get_entities(cleaned_text)
        sentiment = get_sentiment(cleaned_text)
        if sentiment not in {"Positive", "Neutral", "Negative"}:
            sentiment = "Neutral"

        return {
            "status": "success",
            "fileName": payload.fileName,
            "summary": summary,
            "entities": entities,
            "sentiment": sentiment,
        }
    except Exception as exc:
        print(f"[ERROR] Failed to process document: {exc}")
        return _error_response(payload.fileName)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as cleanup_exc:
                print(f"[ERROR] Failed to delete temp file: {cleanup_exc}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port)
