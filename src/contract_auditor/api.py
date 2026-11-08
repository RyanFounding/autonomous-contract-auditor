"""HTTP API: upload a PDF contract, receive a compliance report."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status

from contract_auditor import __version__
from contract_auditor.config import Settings
from contract_auditor.extraction import (
    ContractExtractor,
    DocumentError,
    ExtractionError,
    GeminiContractExtractor,
    read_pdf_text,
)
from contract_auditor.policy import audit
from contract_auditor.schemas import ComplianceReport

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF-"


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def get_extractor(settings: Annotated[Settings, Depends(get_settings)]) -> ContractExtractor:
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured on the server.",
        )
    return GeminiContractExtractor(settings.gemini_api_key, settings.gemini_model)


app = FastAPI(title="Contract Compliance Auditor", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/audit-contract", response_model=ComplianceReport)
def audit_contract(
    file: Annotated[UploadFile, File(description="Vendor contract as a text-based PDF")],
    settings: Annotated[Settings, Depends(get_settings)],
    extractor: Annotated[ContractExtractor, Depends(get_extractor)],
) -> ComplianceReport:
    # Declared as a sync endpoint on purpose: PDF parsing and the model call are
    # blocking, so FastAPI runs this in its worker thread pool instead of
    # stalling the event loop.
    pdf_bytes = file.file.read(settings.max_upload_bytes + 1)
    if len(pdf_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit.",
        )
    if not pdf_bytes.startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported.",
        )

    try:
        contract_text = read_pdf_text(pdf_bytes)
        extraction = extractor.extract(contract_text)
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ExtractionError as exc:
        logger.warning("Extraction failed for %s: %s", file.filename, exc)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail="Contract extraction failed upstream."
        ) from exc

    return audit(extraction, settings.policy)
