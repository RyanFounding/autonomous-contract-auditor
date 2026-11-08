from __future__ import annotations

import pytest
from pydantic import ValidationError

from contract_auditor.policy import CompliancePolicy, audit
from contract_auditor.schemas import ContractExtraction, LineItem

POLICY = CompliancePolicy(max_payment_terms_days=30, max_lead_time_days=21)


def test_contract_at_the_limits_is_compliant(compliant_extraction: ContractExtraction) -> None:
    report = audit(compliant_extraction, POLICY)

    assert report.is_compliant
    assert report.violations == []
    assert report.warnings == []
    assert report.policy.max_payment_terms_days == 30


def test_each_breached_limit_produces_one_violation(
    compliant_extraction: ContractExtraction,
) -> None:
    extraction = compliant_extraction.model_copy(
        update={"payment_terms_days": 60, "lead_time_days": 22}
    )

    report = audit(extraction, POLICY)

    assert not report.is_compliant
    assert [v.rule for v in report.violations] == ["payment_terms", "lead_time"]


def test_custom_policy_limits_are_applied(compliant_extraction: ContractExtraction) -> None:
    strict = CompliancePolicy(max_payment_terms_days=14, max_lead_time_days=7)

    report = audit(compliant_extraction, strict)

    assert {v.rule for v in report.violations} == {"payment_terms", "lead_time"}


def test_value_mismatch_is_a_warning_not_a_violation(
    compliant_extraction: ContractExtraction,
) -> None:
    extraction = compliant_extraction.model_copy(update={"total_contract_value_usd": 12_500.0})

    report = audit(extraction, POLICY)

    assert report.is_compliant
    assert len(report.warnings) == 1
    assert "$10,000.00" in report.warnings[0]
    assert "$2,500.00" in report.warnings[0]


def test_missing_line_items_are_flagged() -> None:
    extraction = ContractExtraction(
        vendor_name="Vendor",
        payment_terms_days=0,
        lead_time_days=0,
        total_contract_value_usd=1.0,
        line_items=[],
    )

    report = audit(extraction, POLICY)

    assert report.warnings == [
        "No line items were extracted; the contract value cannot be verified."
    ]


def test_schema_rejects_negative_values() -> None:
    with pytest.raises(ValidationError):
        LineItem(description="Valve", quantity=-1, unit_price_usd=10.0)
