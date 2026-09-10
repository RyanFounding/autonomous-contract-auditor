from pydantic import BaseModel, Field
from typing import List

class LineItem(BaseModel):
    description: str = Field(description="The name or description of the purchased item/service")
    quantity: int = Field(description="Total quantity ordered")
    unit_price_usd: float = Field(description="Price per individual unit in USD")

class ContractExtraction(BaseModel):
    vendor_name: str = Field(description="The legal name of the vendor supplying the contract")
    payment_terms_days: int = Field(description="Extract the Net payment terms as an integer (e.g., 'Net 30' becomes 30, 'Due upon receipt' becomes 0)")
    lead_time_days: int = Field(description="The delivery lead time in days. If stated in weeks, multiply by 7.")
    total_contract_value_usd: float = Field(description="The total financial value of the contract")
    line_items: List[LineItem] = Field(description="List of all specific items or services being purchased")