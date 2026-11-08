# Contract Compliance Auditor

A FastAPI service that reads a vendor contract PDF, extracts the commercial terms into a typed schema, and checks them against procurement policy.

Live demo: [insan-contract-auditor.streamlit.app](https://insan-contract-auditor.streamlit.app)

## Problem

Procurement teams review vendor contracts for a small set of terms that drive cost and supply risk: payment terms, delivery lead time, and the value of what is being bought. Checking these by hand is slow, and it gets skipped when volume is high. A language model can read the contract, but it should not be the one deciding whether a contract passes policy. Its answers are not reproducible, and nobody can audit them.

## Solution

The service splits the job in two:

1. **Extraction.** A language model (Gemini) turns contract text into a strict Pydantic schema. It does nothing else.
2. **Decision.** Plain Python rules compare the extracted values against configurable policy limits and return a pass/fail report with a reason for every failure.

The model's output is also cross-checked against itself: if the line items don't add up to the stated contract value, the report flags it for human review instead of trusting either number.

## Architecture

```
PDF upload
    |
    v
api.py            validate size and file signature, map errors to HTTP status codes
    |
    v
extraction.py     read text layer in memory (PyMuPDF) -> LLM with response schema
    |                                                    -> ContractExtraction (validated)
    v
policy.py         deterministic rules -> violations (fail)
                  consistency checks  -> warnings (review)
    |
    v
ComplianceReport (JSON)
```

| Module | Responsibility |
|---|---|
| `schemas.py` | Data contracts shared by every layer. Field descriptions double as extraction instructions. |
| `extraction.py` | PDF text extraction and the model call. Raises `DocumentError` or `ExtractionError`, never HTTP errors. |
| `policy.py` | Policy rules and data-quality checks. Pure functions, no I/O. |
| `config.py` | Settings read from environment variables, including policy limits. |
| `api.py` | HTTP layer only. Wires settings and the extractor through FastAPI dependencies. |
| `app.py` | Streamlit demo. Uses the same extraction and policy modules as the API. |

## Tech stack

| Choice | Why |
|---|---|
| FastAPI | Typed request and response models, automatic OpenAPI docs, and dependency injection that lets tests swap out the model client. |
| Pydantic v2 | One schema serves as the model's response format, the validator for its output, and the API contract. |
| PyMuPDF | Fast, reliable text extraction that works on in-memory bytes, so uploads never touch disk. |
| Gemini 2.5 Flash | Supports a JSON response schema natively, which removes free-text parsing. Temperature 0 for repeatable output. |
| pytest, ruff, mypy (strict) | Tests run without an API key or network. CI runs lint, type checks and tests on every push. |

## Key technical decisions

- **The model extracts, the code decides.** Compliance never depends on how the model phrases something. Changing a limit is a config change, not a prompt change.
- **Extractor behind a protocol.** `api.py` depends on a `ContractExtractor` interface. Tests inject a fake, and switching providers means writing one class.
- **Uploads stay in memory.** Earlier versions wrote the upload to disk using the client-supplied filename, which allowed path traversal. Reading bytes directly removes the temp file, the cleanup code and the vulnerability.
- **Specific error codes.** 413 for oversized files, 415 for non-PDFs, 422 for image-only or encrypted PDFs, 502 when the model call fails, 503 when the server has no API key. Upstream error details are logged, not returned to the client.
- **Warnings separate from violations.** A value mismatch doesn't mean the contract breaks policy. It means a person should look. Keeping the two apart stops false failures.

## Running locally

Requires Python 3.11 or newer.

```bash
git clone https://github.com/insan-sll/autonomous-contract-auditor.git
cd autonomous-contract-auditor
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env               # then set GEMINI_API_KEY
```

Start the API. The `--env-file` flag loads your `.env`:

```bash
uvicorn contract_auditor.api:app --reload --env-file .env
```

Audit the bundled sample contract. It has Net 45 terms and a 35-day lead time, so it should fail both rules:

```bash
curl -F "file=@data/sample_contract.pdf" http://127.0.0.1:8000/audit-contract
```

Interactive API docs are at http://127.0.0.1:8000/docs.

### Streamlit demo

A browser front end for the same pipeline. Upload a contract or use the bundled sample, then adjust the policy limits in the sidebar. The model reads the contract once, and changing a limit re-audits instantly without another model call.

```bash
export GEMINI_API_KEY=your-key     # or put it in .env and export it
streamlit run app.py
```

To host it on Streamlit Community Cloud, set the main file to `app.py` and add `GEMINI_API_KEY` under the app's secrets. The deployment installs only `requirements.txt`, which is a smaller set than the API needs.

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | none | Required to call the model. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model used for extraction. |
| `MAX_UPLOAD_MB` | `10` | Upload size limit. |
| `POLICY_MAX_PAYMENT_TERMS_DAYS` | `30` | Longest acceptable payment terms. |
| `POLICY_MAX_LEAD_TIME_DAYS` | `21` | Longest acceptable delivery lead time. |

## Testing

```bash
pytest           # unit and API tests; no API key or network needed
ruff check .     # lint
mypy             # strict type check
```

The tests cover the policy rules, the data-quality checks, PDF parsing edge cases (corrupt, image-only), every HTTP error path, and path-traversal filenames.

## Limitations

- Scanned contracts without a text layer are rejected; there is no OCR step.
- Amounts are assumed to be in USD.
- Extraction quality depends on the model. The consistency check catches some extraction errors, but not all of them.
