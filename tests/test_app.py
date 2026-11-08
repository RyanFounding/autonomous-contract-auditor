from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from contract_auditor.schemas import ContractExtraction, LineItem

APP = str(Path(__file__).resolve().parent.parent / "app.py")


class FakeExtractor:
    """Returns the figures printed on data/sample_contract.pdf without calling a model."""

    def __init__(self, api_key: str, model: str) -> None:
        pass

    def extract(self, contract_text: str) -> ContractExtraction:
        assert "Global Logistics Partners" in contract_text
        return ContractExtraction(
            vendor_name="Global Logistics Partners LLC",
            payment_terms_days=45,
            lead_time_days=35,
            total_contract_value_usd=45_000.0,
            line_items=[
                LineItem(
                    description="Industrial Conveyor Rollers", quantity=30, unit_price_usd=500
                ),
                LineItem(description="Hydraulic Control Valves", quantity=10, unit_price_usd=3000),
            ],
        )


def test_app_asks_for_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP, default_timeout=30).run()

    assert not at.exception
    assert "GEMINI_API_KEY is not set" in at.error[0].value


def test_sample_contract_audit_and_live_policy_change(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("contract_auditor.extraction.GeminiContractExtractor", FakeExtractor)

    at = AppTest.from_file(APP, default_timeout=30).run()
    assert at.info  # prompts for a contract before anything is selected

    at.button(key="use_sample").click().run()
    at.button(key="run_audit").click().run()

    assert not at.exception
    assert "2 policy violation" in at.error[0].value

    # Raising the limits turns the same extraction compliant, with no second model call.
    at.number_input[0].set_value(60).run()
    at.number_input[1].set_value(40).run()

    assert not at.exception
    assert not at.error
    assert "Compliant" in at.success[0].value
