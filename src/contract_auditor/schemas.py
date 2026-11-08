"""Data contracts shared by the extraction layer, the policy engine and the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str = Field(description="Name or description of the purchased item or service")
    quantity: int = Field(ge=0, description="Total quantity ordered")
    unit_price_usd: float = Field(ge=0, description="Price per individual unit in USD")

    @property
    def line_total_usd(self) -> float:
        return self.quantity * self.unit_price_usd


class ContractExtraction(BaseModel):
    """Fields extracted from a vendor contract.

    The field descriptions are sent to the model as part of the response schema,
    so they double as extraction instructions.
    """

    vendor_name: str = Field(description="Legal name of the vendor supplying the contract")
    payment_terms_days: int = Field(
        ge=0,
        description=(
            "Net payment terms as an integer ('Net 30' becomes 30, 'Due upon receipt' becomes 0)"
        ),
    )
    lead_time_days: int = Field(
        ge=0,
        description="Delivery lead time in days. If stated in weeks, multiply by 7.",
    )
    total_contract_value_usd: float = Field(
        ge=0, description="Total financial value of the contract in USD"
    )
    line_items: list[LineItem] = Field(description="Every specific item or service being purchased")


class Violation(BaseModel):
    rule: str = Field(description="Machine-readable identifier of the rule that failed")
    message: str


class PolicyLimits(BaseModel):
    max_payment_terms_days: int
    max_lead_time_days: int
    value_tolerance_usd: float


class ComplianceReport(BaseModel):
    extraction: ContractExtraction
    is_compliant: bool
    violations: list[Violation]
    warnings: list[str] = Field(
        description="Data-quality findings that do not fail compliance but need human review"
    )
    policy: PolicyLimits
