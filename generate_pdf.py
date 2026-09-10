import fitz  # PyMuPDF
from pathlib import Path

# Ensure data directory exists
Path("data").mkdir(exist_ok=True)

# Create a new PDF document
doc = fitz.open()
page = doc.new_page()

# Define contract content that violates corporate policy (Net 45 terms > 30 max, 35 day lead time > 21 max)
contract_text = """
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

# Insert text onto the page
page.insert_textbox(fitz.Rect(50, 50, 550, 700), contract_text, fontsize=12)

# Save the PDF
output_path = "data/sample_contract.pdf"
doc.save(output_path)
doc.close()

print(f"Sample contract successfully generated at {output_path}")