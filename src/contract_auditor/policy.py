"""Deterministic procurement policy checks.

The language model only extracts data. Every pass/fail decision is made here,
in plain Python, so the outcome is reproducible and easy to audit.
"""

from __future__ import annotations

from dataclasses import dataclass

from contract_auditor.schemas import ComplianceReport, ContractExtraction, PolicyLimits, Violation


@dataclass(frozen=True)
class CompliancePolicy:
    max_payment_terms_days: int = 30
    max_lead_time_days: int = 21
    value_tolerance_usd: float = 0.01

    def limits(self) -> PolicyLimits:
        return PolicyLimits(
            max_payment_terms_days=self.max_payment_terms_days,
            max_lead_time_days=self.max_lead_time_days,
            value_tolerance_usd=self.value_tolerance_usd,
        )


def find_violations(extraction: ContractExtraction, policy: CompliancePolicy) -> list[Violation]:
    violations: list[Violation] = []

    if extraction.payment_terms_days > policy.max_payment_terms_days:
        violations.append(
            Violation(
                rule="payment_terms",
                message=(
                    f"Payment terms of {extraction.payment_terms_days} days exceed the "
                    f"maximum of {policy.max_payment_terms_days} days."
                ),
            )
        )

    if extraction.lead_time_days > policy.max_lead_time_days:
        violations.append(
            Violation(
                rule="lead_time",
                message=(
                    f"Lead time of {extraction.lead_time_days} days exceeds the "
                    f"maximum of {policy.max_lead_time_days} days."
                ),
            )
        )

    return violations


def find_data_quality_warnings(
    extraction: ContractExtraction, policy: CompliancePolicy
) -> list[str]:
    """Cross-check extracted figures against each other.

    A mismatch usually means the contract has unlisted charges (freight, tax)
    or the extraction misread a number; either way a person should look.
    """
    warnings: list[str] = []

    if not extraction.line_items:
        warnings.append("No line items were extracted; the contract value cannot be verified.")
        return warnings

    line_sum = round(sum(item.line_total_usd for item in extraction.line_items), 2)
    difference = round(extraction.total_contract_value_usd - line_sum, 2)
    if abs(difference) > policy.value_tolerance_usd:
        warnings.append(
            f"Line items sum to ${line_sum:,.2f} but the stated contract value is "
            f"${extraction.total_contract_value_usd:,.2f} (difference ${difference:,.2f})."
        )

    return warnings


def audit(extraction: ContractExtraction, policy: CompliancePolicy) -> ComplianceReport:
    violations = find_violations(extraction, policy)
    return ComplianceReport(
        extraction=extraction,
        is_compliant=not violations,
        violations=violations,
        warnings=find_data_quality_warnings(extraction, policy),
        policy=policy.limits(),
    )
