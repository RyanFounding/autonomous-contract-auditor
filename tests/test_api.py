from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from contract_auditor.api import app, get_extractor, get_settings
from contract_auditor.config import Settings
from contract_auditor.extraction import ExtractionError
from contract_auditor.schemas import ContractExtraction

MakePdf = Callable[[str | None], bytes]


class FakeExtractor:
    def __init__(self, result: ContractExtraction | Exception) -> None:
        self.result = result
        self.received_text: str | None = None

    def extract(self, contract_text: str) -> ContractExtraction:
        self.received_text = contract_text
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def settings() -> Settings:
    return Settings(gemini_api_key="test-key", max_upload_bytes=1024 * 1024)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.clear()


def use_extractor(extractor: FakeExtractor) -> None:
    app.dependency_overrides[get_extractor] = lambda: extractor


def upload(client: TestClient, content: bytes, name: str = "contract.pdf") -> object:
    return client.post("/audit-contract", files={"file": (name, content, "application/pdf")})


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_compliant_contract(
    client: TestClient, make_pdf: MakePdf, compliant_extraction: ContractExtraction
) -> None:
    extractor = FakeExtractor(compliant_extraction)
    use_extractor(extractor)

    response = client.post(
        "/audit-contract",
        files={"file": ("c.pdf", make_pdf("Vendor: Acme\nPayment Terms: Net 30"), "x")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_compliant"] is True
    assert body["violations"] == []
    assert extractor.received_text is not None
    assert "Net 30" in extractor.received_text


def test_violations_are_reported(
    client: TestClient, make_pdf: MakePdf, compliant_extraction: ContractExtraction
) -> None:
    use_extractor(
        FakeExtractor(
            compliant_extraction.model_copy(update={"payment_terms_days": 60, "lead_time_days": 30})
        )
    )

    response = client.post(
        "/audit-contract", files={"file": ("c.pdf", make_pdf("Net 60"), "application/pdf")}
    )

    assert response.status_code == 200
    assert [v["rule"] for v in response.json()["violations"]] == ["payment_terms", "lead_time"]


def test_path_like_filename_is_harmless(
    client: TestClient, make_pdf: MakePdf, compliant_extraction: ContractExtraction
) -> None:
    use_extractor(FakeExtractor(compliant_extraction))

    response = client.post(
        "/audit-contract",
        files={"file": ("../../etc/evil.pdf", make_pdf("Net 30"), "application/pdf")},
    )

    assert response.status_code == 200


def test_non_pdf_is_rejected(client: TestClient, compliant_extraction: ContractExtraction) -> None:
    use_extractor(FakeExtractor(compliant_extraction))

    response = client.post(
        "/audit-contract", files={"file": ("contract.pdf", b"not a pdf", "application/pdf")}
    )

    assert response.status_code == 415


def test_oversized_upload_is_rejected(
    client: TestClient, settings: Settings, compliant_extraction: ContractExtraction
) -> None:
    use_extractor(FakeExtractor(compliant_extraction))
    payload = b"%PDF-" + b"0" * settings.max_upload_bytes

    response = client.post(
        "/audit-contract", files={"file": ("big.pdf", payload, "application/pdf")}
    )

    assert response.status_code == 413


def test_pdf_without_text_layer_is_unprocessable(
    client: TestClient, make_pdf: MakePdf, compliant_extraction: ContractExtraction
) -> None:
    use_extractor(FakeExtractor(compliant_extraction))

    response = client.post(
        "/audit-contract", files={"file": ("scan.pdf", make_pdf(None), "application/pdf")}
    )

    assert response.status_code == 422
    assert "OCR" in response.json()["detail"]


def test_upstream_failure_returns_502_without_leaking_details(
    client: TestClient, make_pdf: MakePdf
) -> None:
    use_extractor(FakeExtractor(ExtractionError("quota exceeded for key abc123")))

    response = client.post(
        "/audit-contract", files={"file": ("c.pdf", make_pdf("Net 30"), "application/pdf")}
    )

    assert response.status_code == 502
    assert "abc123" not in response.text


def test_missing_api_key_returns_503(make_pdf: MakePdf) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(gemini_api_key=None)
    try:
        response = TestClient(app).post(
            "/audit-contract", files={"file": ("c.pdf", make_pdf("Net 30"), "application/pdf")}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
