"""Streamlit front end for the contract auditor.

Uses the same extraction and policy code as the HTTP API. The model reads the contract once;
the policy check is plain Python, so changing a limit re-audits instantly without another
model call.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SAMPLE_CONTRACT = ROOT / "data" / "sample_contract.pdf"

# Load the application code straight from this checkout. A copy installed into site-packages
# would not update when only the code changes, so the app could run a stale version.
sys.path.insert(0, str(ROOT / "src"))

from contract_auditor.extraction import (  # noqa: E402
    DocumentError,
    ExtractionError,
    GeminiContractExtractor,
    read_pdf_text,
)
from contract_auditor.policy import CompliancePolicy, audit  # noqa: E402
from contract_auditor.schemas import ContractExtraction  # noqa: E402

st.set_page_config(page_title="Contract Compliance Auditor", layout="wide")
st.title("Contract Compliance Auditor")
st.write(
    "Upload a vendor contract as a text-based PDF. A language model extracts the commercial "
    "terms, then plain Python rules decide whether the contract meets your procurement policy."
)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY is not set. Add it to the environment or to Streamlit secrets.")
    st.stop()

model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


@st.cache_resource
def get_extractor(key: str, model_name: str) -> GeminiContractExtractor:
    return GeminiContractExtractor(api_key=key, model=model_name)


with st.sidebar:
    st.header("Procurement policy")
    max_terms = st.number_input("Maximum payment terms (days)", min_value=0, value=30, step=5)
    max_lead = st.number_input("Maximum lead time (days)", min_value=0, value=21, step=1)
    st.caption("Changing a limit updates the result below without calling the model again.")

policy = CompliancePolicy(max_payment_terms_days=int(max_terms), max_lead_time_days=int(max_lead))

uploaded = st.file_uploader("Vendor contract (PDF)", type=["pdf"])
if st.button("Use the bundled sample contract", key="use_sample"):
    st.session_state["contract"] = ("sample_contract.pdf", SAMPLE_CONTRACT.read_bytes())
    st.session_state.pop("extraction", None)
elif uploaded is not None:
    candidate = (uploaded.name, uploaded.getvalue())
    if st.session_state.get("contract") != candidate:
        st.session_state["contract"] = candidate
        st.session_state.pop("extraction", None)

contract: tuple[str, bytes] | None = st.session_state.get("contract")
if contract is None:
    st.info("Upload a contract, or use the bundled sample to see how it works.")
    st.stop()

name, pdf_bytes = contract
fingerprint = hashlib.sha256(pdf_bytes).hexdigest()[:8]
st.caption(f"Selected: {name} ({len(pdf_bytes) / 1024:.0f} KB, id {fingerprint})")

if st.button("Run audit", type="primary", key="run_audit"):
    with st.spinner("Reading the contract..."):
        try:
            text = read_pdf_text(pdf_bytes)
            st.session_state["extraction"] = get_extractor(api_key, model).extract(text)
        except DocumentError as exc:
            st.error(str(exc))
        except ExtractionError:
            st.error("The model could not extract this contract. Check the API key and try again.")

extraction: ContractExtraction | None = st.session_state.get("extraction")
if extraction is None:
    st.stop()

report = audit(extraction, policy)

if report.is_compliant:
    st.success("Compliant: the contract meets every policy limit.")
else:
    st.error(f"Not compliant: {len(report.violations)} policy violation(s).")
    for violation in report.violations:
        st.write(f"- **{violation.rule.replace('_', ' ').title()}:** {violation.message}")

for warning in report.warnings:
    st.warning(f"Needs review: {warning}")

st.subheader("Extracted terms")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendor", extraction.vendor_name)
c2.metric("Payment terms", f"{extraction.payment_terms_days} days")
c3.metric("Lead time", f"{extraction.lead_time_days} days")
c4.metric("Contract value", f"${extraction.total_contract_value_usd:,.2f}")

if extraction.line_items:
    st.dataframe(
        [
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit_price_usd": item.unit_price_usd,
                "line_total_usd": item.line_total_usd,
            }
            for item in extraction.line_items
        ],
        hide_index=True,
    )
