import json
import os
import anthropic
from concurrent.futures import ThreadPoolExecutor

# ──────────────────────────────────────────────────────────────────────────────
#  CLIENT
# ──────────────────────────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ──────────────────────────────────────────────────────────────────────────────
#  FUNCTION 1 — PARSE DOCUMENT
# ──────────────────────────────────────────────────────────────────────────────
def parse_document(doc_text: str) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": f"""You are a legal analyst. Extract these 10 sections from the document below.
Be concise. Use markdown. Bold important terms. Do not stop early — complete ALL 10 sections.

## 1. Document Type
## 2. Parties Involved
## 3. Effective Date & Duration
## 4. Key Obligations
## 5. Payment Terms
## 6. Confidentiality & IP
## 7. Termination Conditions
## 8. Dispute Resolution
## 9. Governing Law
## 10. Special Clauses

DOCUMENT:
{doc_text[:6000]}

Write all 10 sections now:"""
        }]
    )
    return message.content[0].text


# ──────────────────────────────────────────────────────────────────────────────
#  FUNCTION 2 — ANALYSE RISKS
#  Returns a clean LIST of dicts with keys:
#    clause / risk_level / why_its_a_risk / suggestion
# ──────────────────────────────────────────────────────────────────────────────
def analyse_risks(doc_text: str) -> list:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": f"""You are an expert legal risk analyst.

Analyze the legal document and return ONLY a JSON array.

STRICT RULES:
- Your entire response must be a single JSON array, starting with [ and ending with ]
- No text before or after the array
- No markdown, no code fences, no explanation

Each object must have EXACTLY these 4 keys:
{{
  "clause": "a SHORT excerpt (max 20-25 words) of the exact problematic text — not the full paragraph",
  "risk_level": "HIGH or MEDIUM or LOW",
  "why_its_a_risk": "plain English explanation of why this is a risk (1-2 sentences)",
  "suggestion": "specific action the user should take to protect themselves (1-2 sentences)"
}}

Order: HIGH risks first, then MEDIUM, then LOW.
Find ALL risks — do not stop early. Keep each field concise so you can cover every risk
without running out of space.

Look for:
- Unlimited or uncapped liability
- One-sided indemnification
- Vague or undefined key terms
- Auto-renewal with short opt-out window
- Excessive penalty or liquidated damages
- Missing IP ownership protections
- Unfair termination rights
- Overly broad non-compete or non-solicitation clauses
- Unfavourable jurisdiction or governing law
- Missing dispute resolution mechanism
- Unclear data privacy obligations
- Missing force majeure clause
- Assignment rights without consent
- Perpetual confidentiality with no time limit
- Unilateral modification of terms

LEGAL DOCUMENT:
{doc_text[:6000]}"""
        }]
    )

    raw_text = message.content[0].text
    stop_reason = message.stop_reason

    raw = raw_text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    # Try a clean parse first
    try:
        risks = json.loads(raw)
        if isinstance(risks, list):
            return normalize_risks(risks)
        elif isinstance(risks, dict) and "risks" in risks:
            return normalize_risks(risks["risks"])
    except json.JSONDecodeError:
        pass

    # Fallback: salvage whatever complete risk objects exist, even if the
    # response was cut off mid-array (stop_reason == "max_tokens").
    salvaged = extract_valid_risks(raw)
    if salvaged:
        return normalize_risks(salvaged)

    # Last resort — nothing usable could be recovered
    note = ("The AI response was cut off before completing."
            if stop_reason == "max_tokens"
            else "The AI response could not be parsed as JSON.")
    return [{
        "clause": "Full document",
        "risk_level": "MEDIUM",
        "why_its_a_risk": note,
        "suggestion": "Please consult a qualified legal professional.",
    }]


def extract_valid_risks(raw: str) -> list:
    """
    Salvages as many *complete* risk objects as possible from a
    possibly-truncated JSON array, instead of discarding everything
    if the response got cut off mid-way.
    """
    start = raw.find("[")
    if start == -1:
        return []
    text = raw[start:]

    objs = []
    depth = 0
    obj_start = None
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 1 and obj_start is None:
                obj_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 1 and obj_start is not None:
                objs.append(text[obj_start:i + 1])
                obj_start = None
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1

    if not objs:
        return []

    reconstructed = "[" + ",".join(objs) + "]"
    try:
        return json.loads(reconstructed)
    except Exception:
        return []


def normalize_risks(risks: list) -> list:
    """Guarantee every item is a well-formed risk dict before it leaves Lambda."""
    normalized = []
    for r in risks:
        if not isinstance(r, dict):
            continue
        level = str(r.get("risk_level", "MEDIUM")).strip().upper()
        if level not in ("HIGH", "MEDIUM", "LOW"):
            level = "MEDIUM"
        normalized.append({
            "clause":         str(r.get("clause", "Not specified")),
            "risk_level":     level,
            "why_its_a_risk": str(r.get("why_its_a_risk", "")),
            "suggestion":     str(r.get("suggestion", "")),
        })
    return normalized


# ──────────────────────────────────────────────────────────────────────────────
#  RESPONSE BUILDER
# ──────────────────────────────────────────────────────────────────────────────
def respond(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(body),
    }


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN HANDLER
# ──────────────────────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return respond(200, {"message": "OK"})

    try:
        raw  = event.get("body", event)
        body = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return respond(400, {"error": "Request body is not valid JSON."})

    doc_text = body.get("document_text", "").strip()

    if not doc_text:
        return respond(400, {"error": "No document_text in request."})
    if len(doc_text) < 50:
        return respond(400, {"error": "Document too short."})

    word_count = len(doc_text.split())

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_summary = executor.submit(parse_document, doc_text)
            future_risks   = executor.submit(analyse_risks,  doc_text)
            summary = future_summary.result()
            risks   = future_risks.result()

    except anthropic.AuthenticationError:
        return respond(401, {"error": "Invalid ANTHROPIC_API_KEY."})
    except anthropic.RateLimitError:
        return respond(429, {"error": "Rate limit hit. Try again."})
    except anthropic.APIStatusError as e:
        return respond(502, {"error": f"Claude API error {e.status_code}: {e.message}"})
    except anthropic.APIConnectionError:
        return respond(502, {"error": "Could not connect to Anthropic API."})
    except Exception as e:
        return respond(500, {"error": f"Unexpected error: {str(e)}"})

    return respond(200, {
        "summary":    summary,
        "risks":      risks,
        "word_count": word_count,
    })