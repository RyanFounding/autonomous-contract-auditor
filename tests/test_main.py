from fastapi.testclient import TestClient
from unittest.mock import patch
from src.main import app
from src.schemas import ContractExtraction, LineItem

client = TestClient(app)

@patch("src.main.extract_contract_from_pdf")
def test_audit_contract_compliant(mock_extract):
    # Arrange: Mock the extraction engine to return a fully compliant contract
    mock_extract.return_value = ContractExtraction(
        vendor_name="Acme Industrial Logistics",
        payment_terms_days=30,  # Exactly at the limit (Max 30)
        lead_time_days=14,      # Within threshold (Max 21)
        total_contract_value_usd=10000.0,
        line_items=[
            LineItem(description="Hydraulic Pump", quantity=2, unit_price_usd=5000.0)
        ]
    )

    # Act: Send a fake PDF upload request to the FastAPI endpoint
    response = client.post(
        "/audit-contract",
        files={"file": ("test_contract.pdf", b"%PDF-1.4 fake pdf binary content", "application/pdf")}
    )

    # Assert: Verify compliance rules passed successfully
    assert response.status_code == 200
    data = response.json()
    assert data["is_compliant"] is True
    assert len(data["violations"]) == 0
    assert data["extraction"]["vendor_name"] == "Acme Industrial Logistics"


@patch("src.main.extract_contract_from_pdf")
def test_audit_contract_violations(mock_extract):
    # Arrange: Mock extraction to return rule violations (Net 60 terms, 30 day lead time)
    mock_extract.return_value = ContractExtraction(
        vendor_name="Slow Logistics Inc.",
        payment_terms_days=60,  # Violation (> 30 days)
        lead_time_days=30,      # Violation (> 21 days)
        total_contract_value_usd=50000.0,
        line_items=[
            LineItem(description="Conveyor Belt", quantity=1, unit_price_usd=50000.0)
        ]
    )

    # Act: Send request
    response = client.post(
        "/audit-contract",
        files={"file": ("bad_contract.pdf", b"%PDF-1.4 fake content", "application/pdf")}
    )

    # Assert: Verify compliance rules caught both violations
    assert response.status_code == 200
    data = response.json()
    assert data["is_compliant"] is False
    assert len(data["violations"]) == 2
    assert any("Payment terms violation" in v for v in data["violations"])
    assert any("Lead time violation" in v for v in data["violations"])