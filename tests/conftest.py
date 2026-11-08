from __future__ import annotations

from collections.abc import Callable

import pymupdf
import pytest

from contract_auditor.schemas import ContractExtraction, LineItem


def _make_pdf(text: str | None) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    if text:
        page.insert_textbox(pymupdf.Rect(50, 50, 550, 700), text, fontsize=11)
    data: bytes = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def make_pdf() -> Callable[[str | None], bytes]:
    return _make_pdf


@pytest.fixture
def compliant_extraction() -> ContractExtraction:
    return ContractExtraction(
        vendor_name="Acme Industrial Logistics",
        payment_terms_days=30,
        lead_time_days=14,
        total_contract_value_usd=10_000.0,
        line_items=[LineItem(description="Hydraulic Pump", quantity=2, unit_price_usd=5_000.0)],
    )
