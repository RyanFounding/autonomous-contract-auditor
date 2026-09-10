import pytest
from src.schemas import ContractExtraction, LineItem

def test_contract_extraction_schema_validation():
    # Arrange: Create sample structured data as if extracted from a PDF
    raw_data = {
        "vendor_name": "Acme Industrial Logistics",
        "payment_terms_days": 45,
        "lead_time_days": 14,
        "total_contract_value_usd": 15000.0,
        "line_items": [
            {
                "description": "Heavy Duty Actuator",
                "quantity": 10,
                "unit_price_usd": 1500.0
            }
        ]
    }

    # Act: Parse through Pydantic model
    extraction = ContractExtraction(**raw_data)

    # Assert: Validate data contracts hold
    assert extraction.vendor_name == "Acme Industrial Logistics"
    assert extraction.payment_terms_days == 45
    assert extraction.lead_time_days == 14
    assert len(extraction.line_items) == 1
    assert extraction.line_items[0].quantity == 10