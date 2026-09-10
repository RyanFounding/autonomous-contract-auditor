# 📄 Autonomous RFP & Contract Auditing Agent

An enterprise-grade backend service that ingests unstructured PDF vendor contracts, extracts key terms using strict structural schemas, and evaluates compliance against corporate procurement policies.

## 🏗️ Architecture: Deterministic Guardrails over LLM Chaos

Large Language Models are prone to conversational drift and hallucination. This system ensures 100% data reliability by decoupling extraction from policy enforcement:

1. **Extraction Layer (`src/engine.py`):** Uses PyMuPDF to extract text layers and Gemini 2.5 Flash with **Pydantic Structured Outputs (`response_schema`)** to map unstructured text directly into strongly-typed objects. Zero markdown or conversational filler.
2. **Compliance Rule Engine (`src/main.py`):** A FastAPI backend that evaluates extracted integers (such as Net payment terms and lead times) against strict, deterministic Python rule bounds.
3. **Automated Testing (`tests/`):** Pytest suite covering schema validation and mocked FastAPI routing compliance tests.

## 🚀 Quick Start

**1. Clone and set up the environment**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt