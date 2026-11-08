from __future__ import annotations

from collections.abc import Callable

import pytest

from contract_auditor.extraction import DocumentError, read_pdf_text


def test_reads_text_layer(make_pdf: Callable[[str | None], bytes]) -> None:
    text = read_pdf_text(make_pdf("Payment Terms: Net 45"))

    assert "Net 45" in text


def test_image_only_pdf_is_rejected(make_pdf: Callable[[str | None], bytes]) -> None:
    with pytest.raises(DocumentError, match="no text layer"):
        read_pdf_text(make_pdf(None))


def test_corrupt_pdf_is_rejected() -> None:
    with pytest.raises(DocumentError, match="not a readable PDF"):
        read_pdf_text(b"%PDF-1.4 truncated garbage")


def test_bundled_sample_contract_is_readable() -> None:
    from pathlib import Path

    sample = Path(__file__).resolve().parent.parent / "data" / "sample_contract.pdf"

    text = read_pdf_text(sample.read_bytes())

    assert "Net 45" in text
    assert "Global Logistics Partners LLC" in text


def test_client_pins_the_json_schema_capable_api_version(monkeypatch: pytest.MonkeyPatch) -> None:
    from contract_auditor.extraction import GEMINI_API_VERSION, GeminiContractExtractor

    captured: dict[str, object] = {}

    def fake_client(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("google.genai.Client", fake_client)

    GeminiContractExtractor(api_key="test-key", model="gemini-2.5-flash")

    assert GEMINI_API_VERSION == "v1beta"
    assert captured["http_options"].api_version == "v1beta"  # type: ignore[attr-defined]
