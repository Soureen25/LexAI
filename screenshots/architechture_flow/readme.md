## Architecture Diagram


This diagram shows the full request flow of the LexAI Legal Document Analyser, from upload to final downloads.

### Structure
- 🔵 **Frontend** (blue) — Streamlit app (`frontend/app.py`), with each feature boxed as its own section:
  - `doc_preview.py` — Feature #2 (document preview + OCR)
  - `risk_pdf.py` — Feature #1 (PDF risk report)
  - `redline_docx.py` — Feature #4 (redlined docx)
  - Multi-document upload/analyse flow — Feature #3
- 🟡 **Backend** (amber) — AWS Lambda (`backend/lambda_function.py`), where `parse_document()` and `analyse_risks()` run in parallel via `ThreadPoolExecutor`
- 🟣 **External system** — Anthropic Claude API, called twice per document (summary + risk analysis)

### Shape legend

| Shape | Meaning |
|---|---|
| Parallelogram | Input/output (uploads, HTTP payloads, downloaded files) |
| Rounded rectangle | A process or function |
| Diamond | A decision point (e.g., is the page scanned? is the fuzzy-match confident enough?) |
| Cylinder | Data store (`st.session_state.documents`) |
| 3D box | External system (Claude API) |


