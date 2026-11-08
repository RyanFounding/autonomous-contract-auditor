"""Generate data/sample_contract.pdf, a contract that breaches the default policy.

Net 45 payment terms exceed the 30-day limit and a 35-day lead time exceeds the
21-day limit, so the audit should report two violations.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

CONTRACT_TEXT = """
MASTER SERVICES AGREEMENT

Vendor: Global Logistics Partners LLC
Payment Terms: Net 45
Lead Time: 35 days
Total Contract Value: $45,000.00

Line Items:
1. Industrial Conveyor Rollers - Quantity: 30 - Unit Price: $500.00
2. Hydraulic Control Valves - Quantity: 10 - Unit Price: $3,000.00

This agreement binds the parties to the terms specified above upon signature.
"""

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_contract.pdf"


def main() -> None:
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(50, 50, 550, 700), CONTRACT_TEXT, fontsize=12)
        doc.save(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
