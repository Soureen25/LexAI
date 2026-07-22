import streamlit as st
import requests
import PyPDF2
import io
import json
import time
import re
from datetime import datetime

from risk_pdf import generate_risk_pdf
from doc_preview import render_pdf_pages, ocr_image_text, MAX_PREVIEW_PAGES

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
API_URL = "https://vw8pwbjsdd.execute-api.ap-south-1.amazonaws.com/prod/"

# ─────────────────────────────────────────────
#  PAGE SETUP
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="LexAI — Legal Document Analyser",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  STYLING
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@400;600&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #F5F4F0; }

/* Fix ONLY Streamlit native heading backgrounds */
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
.stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
    background: transparent !important;
    color: #0F2137 !important;
    padding: 0 !important;
}

.hero {
    background: #0F2137;
    border-radius: 12px;
    padding: 2.2rem 2.4rem 1.8rem;
    margin-bottom: 1.8rem;
    position: relative;
    overflow: hidden;
}
.hero::after {
    content: "§";
    font-family: 'IBM Plex Serif', serif;
    font-size: 14rem;
    color: rgba(255,255,255,0.04);
    position: absolute;
    right: 1.5rem;
    top: -2rem;
    line-height: 1;
    pointer-events: none;
}
.hero-title {
    font-family: 'IBM Plex Serif', serif;
    font-size: 2.1rem;
    font-weight: 600;
    color: #FFFFFF;
    margin: 0 0 0.4rem;
    line-height: 1.2;
}
.hero-sub { font-size: 0.95rem; color: #A8B8C8; margin: 0; max-width: 560px; }
.hero-badge {
    display: inline-block;
    background: #1E6FA5;
    color: #fff;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    padding: 0.18rem 0.6rem;
    border-radius: 4px;
    margin-bottom: 0.8rem;
    letter-spacing: 0.06em;
}

.metric-row { display: flex; gap: 1rem; margin-bottom: 1.4rem; flex-wrap: wrap; }
.metric-card {
    background: #fff;
    border-radius: 10px;
    padding: 1rem 1.4rem;
    flex: 1;
    min-width: 130px;
    border-top: 3px solid #0F2137;
}
.metric-label { font-size: 0.72rem; color: #6B7280; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.3rem; }
.metric-value { font-family: 'IBM Plex Mono', monospace; font-size: 1.5rem; font-weight: 500; color: #0F2137; }

.badge {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    font-weight: 500;
    padding: 0.22rem 0.65rem;
    border-radius: 4px;
    letter-spacing: 0.05em;
    margin-right: 0.5rem;
}
.badge-high   { background: #FEE2E2; color: #991B1B; }
.badge-medium { background: #FEF3C7; color: #92400E; }
.badge-low    { background: #D1FAE5; color: #065F46; }

.risk-item {
    background: #FAFAFA;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
}

.step-row { display: flex; gap: 0; margin-bottom: 1.8rem; }
.step {
    flex: 1;
    padding: 0.7rem 1rem;
    font-size: 0.82rem;
    color: #9CA3AF;
    border-bottom: 2px solid #E5E7EB;
    text-align: center;
}
.step.active { color: #0F2137; border-bottom: 2px solid #0F2137; font-weight: 600; }
.step.done   { color: #065F46; border-bottom: 2px solid #065F46; }

.stButton > button {
    background: #0F2137 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.55rem 1.8rem !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
}
.stButton > button:hover { background: #1E3A5F !important; }

[data-testid="stSidebar"] { background: #0F2137; }
[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #FFFFFF !important; }
[data-testid="stSidebar"] hr  { border-color: #1E3A5F !important; }

[data-testid="stFileUploader"] { background: #fff; border-radius: 10px; padding: 0.5rem; }

.divider { border: none; border-top: 1px solid #E5E7EB; margin: 1.4rem 0; }

/* ── Summary container ── */
.summary-container {
    background: #ffffff;
    border-radius: 12px;
    padding: 1.6rem 2rem;
    border-left: 4px solid #0F2137;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.summary-container h1,
.summary-container h2,
.summary-container h3,
.summary-container h4 {
    font-family: 'IBM Plex Serif', serif;
    color: #0F2137;
    background: transparent;
    padding: 0;
    margin: 1rem 0 0.4rem;
}
.summary-container p,
.summary-container li { font-size: 0.93rem; color: #374151; line-height: 1.7; }
.summary-container strong { color: #0F2137; }
.summary-container hr { border: none; border-top: 1px solid #E5E7EB; margin: 1rem 0; }
.summary-container table { border-collapse: collapse; width: 100%; margin: 0.8rem 0; font-size: 0.88rem; }
.summary-container th { background: #F3F4F6; color: #0F2137; font-weight: 600; padding: 0.5rem 0.8rem; border: 1px solid #E5E7EB; text-align: left; }
.summary-container td { color: #374151; padding: 0.5rem 0.8rem; border: 1px solid #E5E7EB; }
.summary-container blockquote { border-left: 3px solid #1E6FA5; padding: 0.3rem 0.8rem; margin: 0.5rem 0; background: #EFF6FF; border-radius: 0 4px 4px 0; }
.summary-container blockquote p { color: #1E3A5F; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def extract_pdf_text(file_bytes: bytes) -> str:
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def call_api(document_text: str) -> dict:
    response = requests.post(
        API_URL,
        json={"document_text": document_text},
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data.get("body"), str):
        return json.loads(data["body"])
    return data


def resolve_risks(raw_risks) -> list:
    """
    Handles all formats Lambda might return:
      Case 1 → clean list of dicts           → use directly
      Case 2 → JSON nested in why_its_a_risk → unwrap
      Case 3 → plain string                  → parse or wrap
      Case 4 → empty                         → return []
    """
    if isinstance(raw_risks, str):
        raw_risks = raw_risks.strip()
        try:
            parsed = json.loads(raw_risks)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [{"clause": "Full document", "risk_level": "MEDIUM",
                 "why_its_a_risk": raw_risks,
                 "suggestion": "Consult a legal professional."}]

    if not raw_risks:
        return []

    if isinstance(raw_risks, list) and len(raw_risks) > 0:
        first = raw_risks[0]

        # Guard: only treat as a normal risk dict if it actually is one
        if not isinstance(first, dict):
            if isinstance(first, list):
                return first  # unwrap one level of accidental nesting
            return []

        why = first.get("why_its_a_risk", "")
        # Detect nested JSON inside why_its_a_risk
        if isinstance(why, str) and why.strip().startswith("["):
            try:
                nested = json.loads(why.strip())
                if isinstance(nested, list):
                    return nested
            except Exception:
                pass
        return raw_risks

    return []


def count_risks_by_level(risks: list) -> dict:
    counts = {"high": 0, "medium": 0, "low": 0, "unclassified": 0}
    for risk in risks:
        if not isinstance(risk, dict):
            continue
        level = str(risk.get("risk_level", "")).strip().upper()
        if level == "HIGH":
            counts["high"] += 1
        elif level == "MEDIUM":
            counts["medium"] += 1
        elif level == "LOW":
            counts["low"] += 1
        else:
            counts["unclassified"] += 1
    return counts


def clean_summary(text: str) -> str:
    """Remove leading # h1 title that shows as raw text inside HTML div."""
    lines = text.splitlines()
    cleaned = []
    skip_first_h1 = True
    for line in lines:
        if skip_first_h1 and line.strip().startswith("# "):
            skip_first_h1 = False
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def extract_doc_type(summary_text: str):
    """Pull a short label out of the '## 1. Document Type' section of the summary,
    so each uploaded document can be identified at a glance (e.g. 'NDA', 'Lease')."""
    if not summary_text:
        return None
    match = re.search(r"#+\s*1\.\s*Document Type\s*\n+(.+?)(?:\n#+|\Z)", summary_text, re.DOTALL)
    if not match:
        return None
    first_line = match.group(1).strip().splitlines()[0]
    first_line = re.sub(r"\*\*(.+?)\*\*", r"\1", first_line).strip(" -*:")
    return first_line[:60] if first_line else None


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚖️ LexAI")
    st.markdown("*Legal intelligence, powered by Claude*")
    st.markdown("---")
    st.markdown("### How to use")
    st.markdown("1. Upload one or more PDF/TXT documents\n2. Preview a document, then click **Analyse** on it\n3. Switch between analysed documents to review\n4. Download reports per document")
    st.markdown("---")
    st.markdown("### What gets analysed")
    st.markdown("- Document type & parties\n- Key dates & deadlines\n- Obligations & payment terms\n- Termination clauses\n- Governing law\n- Liability & indemnification risks\n- Vague or unfair language\n- Auto-renewal & penalty traps")
    st.markdown("---")
    st.markdown("### Supported formats")
    st.markdown("📄 PDF &nbsp;&nbsp; 🗒️ TXT")
    st.markdown("---")
    st.caption("⚠️ Not a substitute for legal advice.")
    st.caption(f"Session started: {datetime.now().strftime('%d %b %Y, %H:%M')}")


# ─────────────────────────────────────────────
#  HERO
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-badge">POWERED BY AWS LAMBDA + CLAUDE AI</div>
    <div class="hero-title">Legal Document Analyser</div>
    <p class="hero-sub">
        Upload any contract, NDA, lease, or agreement — one at a time or in batches.
        Get an instant plain-English summary and a structured risk report in under a minute.
    </p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  STATE
# ─────────────────────────────────────────────
def render_steps(active: int):
    steps = ["① Upload", "② Analyse", "③ Review"]
    html = '<div class="step-row">'
    for i, label in enumerate(steps, 1):
        cls = "done" if i < active else ("active" if i == active else "")
        html += f'<div class="step {cls}">{label}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


if "documents"  not in st.session_state: st.session_state.documents  = {}   # key -> doc record
if "active_doc" not in st.session_state: st.session_state.active_doc = None


# ─────────────────────────────────────────────
#  UPLOAD
# ─────────────────────────────────────────────
docs_before      = st.session_state.documents
any_analysed_yet = any(d.get("result") for d in docs_before.values())
render_steps(1 if not docs_before else (3 if any_analysed_yet else 2))

uploaded_files = st.file_uploader(
    "Drop one or more legal documents here",
    type=["pdf", "txt"],
    accept_multiple_files=True,
    help="Max recommended size: 5 MB each. Scanned/image PDFs are not supported.",
)

if uploaded_files:
    current_keys = set()
    for f in uploaded_files:
        key = f"{f.name}__{f.size}"
        current_keys.add(key)
        if key in st.session_state.documents:
            continue  # already extracted — don't redo work on every rerun

        file_bytes = f.read()
        if f.name.lower().endswith(".pdf"):
            with st.spinner(f"Reading {f.name}…"):
                document_text = extract_pdf_text(file_bytes)
            file_type_label = "PDF"
        else:
            document_text = file_bytes.decode("utf-8", errors="ignore")
            file_type_label = "TXT"

        st.session_state.documents[key] = {
            "name":          f.name,
            "file_bytes":    file_bytes,
            "file_type":     file_type_label,
            "document_text": document_text,
            "words":         len(document_text.split()),
            "size_kb":       len(file_bytes) / 1024,
            "result":        None,
            "risks_list":    None,
            "risk_counts":   None,
            "doc_type":      None,
            "elapsed":       None,
            "error":         None,
        }

    # Keep session state in sync with what's currently attached to the uploader —
    # if the user removes a file from the widget, drop it from our records too.
    for key in list(st.session_state.documents.keys()):
        if key not in current_keys:
            del st.session_state.documents[key]
            if st.session_state.active_doc == key:
                st.session_state.active_doc = None

docs = st.session_state.documents

if docs:
    no_text_docs = [d["name"] for d in docs.values() if not d["document_text"].strip()]
    if no_text_docs:
        st.error(
            f"⚠️ Could not extract any text from: {', '.join(no_text_docs)}. "
            "These may be scanned image PDFs and will be skipped."
        )

    # ── Document overview ────────────────────────────────────────────────────
    st.markdown("#### 📚 Uploaded Documents")
    st.caption("Preview each document below, then click **Analyse** on the one you want reviewed.")
    header = st.columns([2.4, 0.8, 1, 1, 1.6, 1.2, 1.3])
    for col, label in zip(header, ["Name", "Type", "Size", "Words", "Identified As", "Status", "Action"]):
        col.markdown(f"<span style='font-size:0.72rem;color:#6B7280;text-transform:uppercase;"
                      f"letter-spacing:0.06em;font-weight:600;'>{label}</span>", unsafe_allow_html=True)

    analyse_key = None  # set if the user clicks Analyse/Re-analyse on a specific row this run

    for key, d in docs.items():
        if d.get("error"):
            status = "⚠️ Error"
        elif d.get("result"):
            status = "✅ Analysed"
        else:
            status = "⏳ Pending"

        row = st.columns([2.4, 0.8, 1, 1, 1.6, 1.2, 1.3])
        row[0].markdown(f"**{d['name']}**")
        row[1].markdown(d["file_type"])
        row[2].markdown(f"{d['size_kb']:.1f} KB")
        row[3].markdown(f"{d['words']:,}")
        row[4].markdown(d.get("doc_type") or "—")
        row[5].markdown(status)

        with row[6]:
            can_analyse = bool(d["document_text"].strip())
            if d.get("result"):
                btn_label = "🔄 Re-analyse"
            else:
                btn_label = "▶ Analyse"
            if st.button(btn_label, key=f"analysebtn_{key}", use_container_width=True, disabled=not can_analyse):
                analyse_key = key

        if d.get("error"):
            st.caption(f"⚠️ {d['name']}: {d['error']}")

        with st.expander(f"👁️ Preview — {d['name']}", expanded=False):
            if d["file_type"] == "PDF":
                try:
                    pages, total_pages, scanned_flags = render_pdf_pages(d["file_bytes"])
                    if total_pages > MAX_PREVIEW_PAGES:
                        st.caption(f"Showing first {MAX_PREVIEW_PAGES} of {total_pages} pages.")
                    for i, (page_png, is_scanned) in enumerate(zip(pages, scanned_flags), 1):
                        st.image(page_png, caption=f"Page {i} of {total_pages}", use_container_width=True)
                        if is_scanned:
                            ocr_state_key = f"ocr_{key}_{i}"
                            if st.button("📝 View extracted text (OCR)", key=f"ocrbtn_{key}_{i}"):
                                with st.spinner("Running OCR on this page…"):
                                    st.session_state[ocr_state_key] = ocr_image_text(page_png)
                            if ocr_state_key in st.session_state:
                                st.text_area(
                                    "OCR text — image was low-resolution; this is Tesseract's best "
                                    "reading of it and may contain small errors.",
                                    value=st.session_state[ocr_state_key],
                                    height=200, key=f"ocrbox_{key}_{i}",
                                )
                except Exception as e:
                    st.warning(f"Could not render preview: {e}")
            else:
                st.text_area("", value=d["document_text"], height=300,
                              label_visibility="collapsed", key=f"preview_txt_{key}")
            st.download_button(
                "⬇️ Download Original", data=d["file_bytes"], file_name=d["name"],
                mime="application/pdf" if d["file_type"] == "PDF" else "text/plain",
                key=f"predl_{key}",
            )

    render_steps(2)

    if analyse_key:
        d = st.session_state.documents[analyse_key]
        progress = st.progress(0, text=f"Sending {d['name']} to AWS Lambda…")
        t0 = time.time()
        try:
            progress.progress(15, text="Lambda received request…")
            res = call_api(d["document_text"])
            progress.progress(90, text="Processing results…")
            time.sleep(0.3)
            progress.progress(100, text="Done!")
            time.sleep(0.3)
            progress.empty()

            if res.get("error"):
                st.session_state.documents[analyse_key]["error"] = res["error"]
            else:
                risks_list = resolve_risks(res.get("risks", []))
                st.session_state.documents[analyse_key].update({
                    "result":      res,
                    "risks_list":  risks_list,
                    "risk_counts": count_risks_by_level(risks_list),
                    "doc_type":    extract_doc_type(res.get("summary", "")),
                    "elapsed":     round(time.time() - t0, 1),
                    "error":       None,
                })
                st.session_state.active_doc = analyse_key

        except requests.exceptions.Timeout:
            progress.empty()
            st.session_state.documents[analyse_key]["error"] = "Request timed out."
        except requests.exceptions.ConnectionError:
            progress.empty()
            st.session_state.documents[analyse_key]["error"] = "Could not connect to the API."
        except requests.exceptions.HTTPError as e:
            progress.empty()
            st.session_state.documents[analyse_key]["error"] = f"HTTP {e.response.status_code} from API."
        except Exception as e:
            progress.empty()
            st.session_state.documents[analyse_key]["error"] = str(e)

        st.rerun()


# ─────────────────────────────────────────────
#  RESULTS
# ─────────────────────────────────────────────
analysed_docs = {k: d for k, d in st.session_state.documents.items() if d.get("result")}

if analysed_docs:
    total_high   = sum(d["risk_counts"]["high"]   for d in analysed_docs.values())
    total_medium = sum(d["risk_counts"]["medium"] for d in analysed_docs.values())
    total_low    = sum(d["risk_counts"]["low"]    for d in analysed_docs.values())

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="metric-label">Documents Analysed</div>
            <div class="metric-value">{len(analysed_docs)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">🔴 Total High Risks</div>
            <div class="metric-value" style="color:#991B1B;">{total_high}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">🟠 Total Medium Risks</div>
            <div class="metric-value" style="color:#92400E;">{total_medium}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">🟢 Total Low Risks</div>
            <div class="metric-value" style="color:#065F46;">{total_low}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Document switcher ────────────────────────────────────────────────────
    keys_list = list(analysed_docs.keys())
    labels = [f"{analysed_docs[k]['name']}  —  {analysed_docs[k].get('doc_type') or 'Document'}" for k in keys_list]
    if st.session_state.active_doc not in keys_list:
        st.session_state.active_doc = keys_list[0]
    default_idx = keys_list.index(st.session_state.active_doc)

    selected_label = st.radio("Select a document to review:", labels, index=default_idx, horizontal=True)
    active_key = keys_list[labels.index(selected_label)]
    st.session_state.active_doc = active_key

    meta         = analysed_docs[active_key]
    result       = meta["result"]
    summary_text = result.get("summary", "")
    risks_list   = meta["risks_list"]
    risk_counts  = meta["risk_counts"]

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="metric-label">Document</div>
            <div class="metric-value" style="font-size:0.95rem;">{meta.get('name','—')}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Words Analysed</div>
            <div class="metric-value">{meta.get('words',0):,}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">🔴 High Risks</div>
            <div class="metric-value" style="color:#991B1B;">{risk_counts['high']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">🟠 Medium Risks</div>
            <div class="metric-value" style="color:#92400E;">{risk_counts['medium']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">🟢 Low Risks</div>
            <div class="metric-value" style="color:#065F46;">{risk_counts['low']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Time Taken</div>
            <div class="metric-value">{meta.get('elapsed','?')}s</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_preview, tab_summary, tab_risks, tab_raw = st.tabs(
        ["👁️ Document Preview", "📋 Document Summary", "⚠️ Risk Analysis", "📄 Raw Text"]
    )

    # ── Preview ──────────────────────────────────────────────────────────────
    with tab_preview:
        st.markdown("""
        <div style="margin-bottom:1rem;">
            <h3 style="color:#0F2137;background:transparent;font-family:'IBM Plex Serif',serif;
                       font-size:1.3rem;margin:0 0 0.3rem;padding:0;">Document Preview</h3>
            <p style="color:#6B7280;font-size:0.85rem;margin:0;">
                View the original document without leaving the app.
            </p>
        </div>
        """, unsafe_allow_html=True)

        file_bytes = meta.get("file_bytes")
        file_type  = meta.get("file_type", "TXT")
        doc_text   = meta.get("document_text", "")

        if not file_bytes:
            st.info("Original file not available for this session — re-upload to preview it.")
        elif file_type == "PDF":
            try:
                pages, total_pages, scanned_flags = render_pdf_pages(file_bytes)
                if total_pages > MAX_PREVIEW_PAGES:
                    st.caption(
                        f"Showing first {MAX_PREVIEW_PAGES} of {total_pages} pages. "
                        "Download the original below to see the rest."
                    )
                page_cols = st.columns([3, 1])
                with page_cols[1]:
                    st.download_button(
                        "⬇️ Download Original",
                        data=file_bytes,
                        file_name=meta.get("name", "document.pdf"),
                        mime="application/pdf",
                        key=f"resdl_{active_key}",
                    )
                for i, (page_png, is_scanned) in enumerate(zip(pages, scanned_flags), 1):
                    st.image(page_png, caption=f"Page {i} of {total_pages}", use_container_width=True)
                    if is_scanned:
                        ocr_state_key = f"ocr_{active_key}_{i}"
                        if st.button("📝 View extracted text (OCR)", key=f"ocrbtn_res_{active_key}_{i}"):
                            with st.spinner("Running OCR on this page…"):
                                st.session_state[ocr_state_key] = ocr_image_text(page_png)
                        if ocr_state_key in st.session_state:
                            st.text_area(
                                "OCR text — image was low-resolution; this is Tesseract's best "
                                "reading of it and may contain small errors.",
                                value=st.session_state[ocr_state_key],
                                height=200, key=f"ocrbox_res_{active_key}_{i}",
                            )
            except Exception as e:
                st.warning(f"Could not render PDF preview: {e}")
        else:
            st.download_button(
                "⬇️ Download Original",
                data=file_bytes,
                file_name=meta.get("name", "document.txt"),
                mime="text/plain",
                key=f"resdl_{active_key}",
            )
            st.text_area("", value=doc_text, height=500, label_visibility="collapsed")

    # ── Summary ───────────────────────────────────────────────────────────────
    with tab_summary:
        st.markdown("""
        <div style="margin-bottom:1rem;">
            <h3 style="color:#0F2137;background:transparent;font-family:'IBM Plex Serif',serif;
                       font-size:1.3rem;margin:0 0 0.3rem;padding:0;">Document Summary</h3>
            <p style="color:#6B7280;font-size:0.85rem;margin:0;">
                Extracted and structured by Claude AI from your document.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if summary_text:
            st.markdown(
                f'<div class="summary-container">{clean_summary(summary_text)}</div>',
                unsafe_allow_html=True
            )
        else:
            st.warning("No summary returned. Check your Lambda function.")

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.download_button(
            "⬇️ Download Summary (.txt)",
            data=summary_text,
            file_name=f"summary_{meta.get('name','doc').rsplit('.',1)[0]}.txt",
            mime="text/plain",
            key=f"summarydl_{active_key}",
        )

    # ── Risks ─────────────────────────────────────────────────────────────────
    with tab_risks:
        st.markdown("""
        <div style="margin-bottom:1rem;">
            <h3 style="color:#0F2137;background:transparent;font-family:'IBM Plex Serif',serif;
                       font-size:1.3rem;margin:0 0 0.3rem;padding:0;">⚠️ Risk Analysis</h3>
            <p style="color:#6B7280;font-size:0.85rem;margin:0;">
                Flagged clauses identified by Claude AI. Each card shows the clause, why it is risky, and what to do.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if risks_list:
            col_f1, col_f2, col_f3 = st.columns(3)
            show_high   = col_f1.checkbox("🔴 High",   value=True, key=f"fh_{active_key}")
            show_medium = col_f2.checkbox("🟠 Medium", value=True, key=f"fm_{active_key}")
            show_low    = col_f3.checkbox("🟢 Low",    value=True, key=f"fl_{active_key}")

            colors = {"HIGH": "#991B1B", "MEDIUM": "#92400E", "LOW": "#065F46"}
            icons  = {"HIGH": "🔴",      "MEDIUM": "🟠",       "LOW": "🟢"}

            shown = 0
            for risk in risks_list:
                level      = risk.get("risk_level", "LOW").upper()
                clause     = risk.get("clause",         "Not specified")
                why        = risk.get("why_its_a_risk", "")
                suggestion = risk.get("suggestion",     "")

                if level == "HIGH"   and not show_high:   continue
                if level == "MEDIUM" and not show_medium: continue
                if level == "LOW"    and not show_low:    continue

                st.markdown(f"""
                <div class="risk-item" style="border-left:4px solid {colors.get(level,'#9CA3AF')};">
                    <div style="margin-bottom:0.8rem;">
                        <span class="badge badge-{level.lower()}">{icons.get(level,'')} {level}</span>
                    </div>
                    <p style="font-size:0.72rem;color:#6B7280;text-transform:uppercase;
                              letter-spacing:0.08em;margin:0 0 0.3rem;">Flagged Clause</p>
                    <div style="background:#F3F4F6;border-left:3px solid #9CA3AF;padding:0.5rem 0.8rem;
                                border-radius:4px;font-style:italic;font-size:0.85rem;
                                color:#374151;margin-bottom:0.8rem;">📌 {clause}</div>
                    <p style="font-size:0.72rem;color:#6B7280;text-transform:uppercase;
                              letter-spacing:0.08em;margin:0 0 0.3rem;">Why It's a Risk</p>
                    <p style="font-size:0.88rem;color:#374151;line-height:1.6;margin-bottom:0.8rem;">
                        {why}</p>
                    <div style="background:#EFF6FF;border-radius:6px;padding:0.6rem 0.8rem;
                                border-left:3px solid #1E6FA5;">
                        <p style="font-size:0.72rem;color:#1E40AF;font-weight:600;
                                  text-transform:uppercase;letter-spacing:0.05em;margin:0 0 0.2rem;">
                            💡 Suggestion</p>
                        <p style="font-size:0.88rem;color:#1E3A5F;margin:0;">{suggestion}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                shown += 1

            if shown == 0:
                st.info("No risks match the selected filters.")
        else:
            st.warning("No risk analysis returned. Check your Lambda function.")

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        if risks_list:
            try:
                pdf_bytes = generate_risk_pdf(
                    risks_list,
                    doc_name=meta.get("name", "document"),
                    word_count=meta.get("words", 0),
                )
                st.download_button(
                    "⬇️ Download Risk Report (.pdf)",
                    data=pdf_bytes,
                    file_name=f"risk_report_{meta.get('name','doc').rsplit('.',1)[0]}.pdf",
                    mime="application/pdf",
                    key=f"riskpdf_{active_key}",
                )
            except Exception as e:
                st.error(f"Could not generate PDF report: {e}")

    # ── Raw Text ──────────────────────────────────────────────────────────────
    with tab_raw:
        st.markdown("""
        <div style="margin-bottom:1rem;">
            <h3 style="color:#0F2137;background:transparent;font-family:'IBM Plex Serif',serif;
                       font-size:1.3rem;margin:0 0 0.3rem;padding:0;">Extracted Document Text</h3>
            <p style="color:#6B7280;font-size:0.85rem;margin:0;">
                The raw text extracted from your file and sent to Lambda.
            </p>
        </div>
        """, unsafe_allow_html=True)
        raw = meta.get("document_text") or result.get("document_text", "")
        if not raw:
            st.info("Raw text is not available for this session.")
        else:
            st.text_area("", value=raw, height=450, label_visibility="collapsed")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    if st.button("🔄 Start Over (clear all documents)"):
        st.session_state.documents  = {}
        st.session_state.active_doc = None
        st.rerun()

elif not docs:
    st.markdown("""
    <div style="text-align:center; padding:3.5rem 1rem; color:#9CA3AF;">
        <div style="font-size:3rem; margin-bottom:0.8rem;">📂</div>
        <h3 style="color:#6B7280;background:transparent;font-family:'IBM Plex Serif',serif;">
            Upload one or more documents to get started</h3>
        <p style="max-width:420px;margin:0 auto;font-size:0.9rem;color:#9CA3AF;">
            Contracts · NDAs · Employment Agreements · Leases · Terms of Service · Partnership Deeds
        </p>
    </div>
    """, unsafe_allow_html=True)