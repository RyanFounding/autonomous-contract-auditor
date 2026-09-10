from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import shutil
import os
from pathlib import Path
from src.engine import extract_contract_from_pdf
from src.schemas import ContractExtraction

app = FastAPI(title="Autonomous Contract Auditor", version="1.0.0")

# Internal Company Compliance Policies
MAX_PAYMENT_TERMS_DAYS = 30
MAX_LEAD_TIME_DAYS = 21

class ComplianceReport(BaseModel):
    extraction: ContractExtraction
    is_compliant: bool
    violations: list[str]

@app.post("/audit-contract", response_model=ComplianceReport)
async def audit_contract(file: UploadFile = File(...)):
    """
    Ingests a vendor PDF contract, extracts data using Gemini structured outputs,
    and checks it against corporate compliance rules.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Save uploaded file temporarily
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_path = temp_dir / file.filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Run extraction engine
        extraction = extract_contract_from_pdf(str(file_path))
        
        # Evaluate compliance rules deterministically
        violations = []
        if extraction.payment_terms_days > MAX_PAYMENT_TERMS_DAYS:
            violations.append(
                f"Payment terms violation: {extraction.payment_terms_days} days exceeds maximum allowed limit of {MAX_PAYMENT_TERMS_DAYS} days."
            )
            
        if extraction.lead_time_days > MAX_LEAD_TIME_DAYS:
            violations.append(
                f"Lead time violation: {extraction.lead_time_days} days exceeds maximum allowed threshold of {MAX_LEAD_TIME_DAYS} days."
            )
            
        is_compliant = len(violations) == 0
        
        return ComplianceReport(
            extraction=extraction,
            is_compliant=is_compliant,
            violations=violations
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Clean up temp file
        if file_path.exists():
            os.remove(file_path)