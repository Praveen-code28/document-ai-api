# AI-Powered Document Analysis & Extraction

A production-focused FastAPI project built for the GUVI Hackathon to analyze documents from multiple formats and return structured NLP insights through a single API.

## Description

This project solves the problem of extracting meaningful information from unstructured documents (PDFs, DOCX files, and images) in a standardized, machine-friendly format. It is designed for automated evaluation and real-world backend reliability with strict request/response handling, safe error fallbacks, and modular processing.

## Features

- Multi-format document ingestion:
  - PDF processing
  - DOCX processing
  - Image processing
- OCR support for image text extraction via Tesseract
- Named entity extraction (names, dates, organizations, amounts)
- Concise text summarization
- Sentiment analysis with normalized output labels
- Secure API key validation
- Robust failure handling with consistent JSON responses

## Tech Stack

- **Backend API:** FastAPI
- **NLP (Entities):** spaCy (`en_core_web_sm`)
- **Summarization:** Hugging Face Transformers (`t5-small`)
- **Sentiment:** TextBlob
- **PDF Extraction:** PyMuPDF (`fitz`)
- **DOCX Extraction:** python-docx
- **OCR:** pytesseract + Pillow + Tesseract OCR
- **Config Management:** python-dotenv

## Setup Instructions

### 1) Clone the repository

```bash
git clone <your-repo-url>
cd document-ai-api
```

### 2) Create and activate virtual environment (recommended)

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

### 3) Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4) Install spaCy English model

```bash
python -m spacy download en_core_web_sm
```

### 5) Install Tesseract OCR

- Download and install Tesseract OCR for your OS.
- Ensure `tesseract` is available in your system PATH.
- Optional: set `TESSERACT_CMD` in `.env` if needed.

### 6) Configure environment variables

Create/update `.env`:

```env
API_KEY=your_secret_key
```

### 7) Run the server

```bash
uvicorn src.main:app --reload
```

Server will start at:

- `http://127.0.0.1:8000`
- Interactive docs: `http://127.0.0.1:8000/docs`

## Deploy on Render

Create a **Web Service** on Render and use:

- **Build Command**

```bash
pip install -r requirements.txt && python -m spacy download en_core_web_sm
```

- **Start Command**

```bash
uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

Set these environment variables in Render:

- `API_KEY` = your production API key (required)
- `TESSERACT_CMD` = optional absolute path to `tesseract` executable if PATH is not configured

Notes for stable deployment:

- The API already reads `API_KEY` via `python-dotenv`/environment variables.
- The app includes a safe `PORT` fallback and `0.0.0.0` binding in `src/main.py`.
- Keep OCR enabled only when Tesseract is installed in the runtime image.

## API Usage

### Endpoint

- **Method:** `POST`
- **Path:** `/api/document-analyze`

### Headers

```http
x-api-key: your_secret_key
Content-Type: application/json
```

### Request Body (JSON)

```json
{
  "fileName": "invoice.pdf",
  "fileType": "pdf",
  "fileBase64": "BASE64_ENCODED_FILE_CONTENT"
}
```

### Success Response (JSON)

```json
{
  "status": "success",
  "fileName": "invoice.pdf",
  "summary": "Concise summary of the extracted content.",
  "entities": {
    "names": ["John Doe"],
    "dates": ["12 March 2026"],
    "organizations": ["ABC Pvt Ltd"],
    "amounts": ["$1,200.00", "INR 5000"]
  },
  "sentiment": "Neutral"
}
```

### Error Response (JSON)

```json
{
  "status": "error",
  "fileName": "invoice.pdf",
  "summary": "",
  "entities": {
    "names": [],
    "dates": [],
    "organizations": [],
    "amounts": []
  },
  "sentiment": "Neutral"
}
```

## Approach

1. **Input Validation & Security**
   - Validates `x-api-key`.
   - Accepts only supported file types (`pdf`, `docx`, `image`).
   - Decodes Base64 safely.

2. **Temporary File Handling**
   - Writes decoded content to a temporary file.
   - Guarantees cleanup after processing.

3. **Text Extraction Pipeline**
   - `pdf` -> PyMuPDF extracts text across all pages.
   - `docx` -> python-docx extracts paragraph content.
   - `image` -> pytesseract OCR extracts text from image.

4. **NLP Processing**
   - **Entity Extraction:** spaCy NER + regex money detection, followed by normalization and deduplication.
   - **Summarization:** `t5-small` on bounded text length for speed and stability.
   - **Sentiment Analysis:** TextBlob polarity mapped strictly to `Positive`, `Neutral`, or `Negative`.

5. **Reliability Guarantees**
   - Graceful error handling across all stages.
   - Consistent, strict JSON response contract.
   - Defensive fallbacks to avoid API crashes.

## Notes

- No hardcoded analysis outputs are used.
- Built to handle unknown and varied document content.
- Optimized for hackathon API testing: strict schema, stable behavior, and lightweight inference choices.
