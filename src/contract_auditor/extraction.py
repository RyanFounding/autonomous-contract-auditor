"""PDF text extraction and LLM-based structured field extraction."""

from __future__ import annotations

from typing import Protocol

import pymupdf
from pydantic import ValidationError

from contract_auditor.schemas import ContractExtraction

EXTRACTION_PROMPT = (
    "Extract the requested fields from the vendor contract below. "
    "Use only information stated in the contract.\n\n"
    "Contract text:\n{contract_text}"
)


class DocumentError(ValueError):
    """The uploaded document cannot be processed (corrupt, encrypted or image-only)."""


class ExtractionError(RuntimeError):
    """The model call failed or returned data that does not match the schema."""


class ContractExtractor(Protocol):
    def extract(self, contract_text: str) -> ContractExtraction: ...


def read_pdf_text(pdf_bytes: bytes) -> str:
    """Return the text layer of a PDF held in memory."""
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:  # type: ignore[no-untyped-call]
            if doc.needs_pass:
                raise DocumentError("The PDF is password-protected.")
            text = "".join(page.get_text() for page in doc)
    except DocumentError:
        raise
    except Exception as exc:  # PyMuPDF raises several unrelated types for bad input
        raise DocumentError("The file is not a readable PDF.") from exc

    if not text.strip():
        raise DocumentError(
            "The PDF has no text layer. Scanned contracts need OCR before they can be audited."
        )
    return text


class GeminiContractExtractor:
    """Calls Gemini with the Pydantic schema as a strict response schema."""

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def extract(self, contract_text: str) -> ContractExtraction:
        from google.genai import types

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=EXTRACTION_PROMPT.format(contract_text=contract_text),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ContractExtraction,
                    temperature=0.0,
                ),
            )
        except Exception as exc:
            raise ExtractionError(f"Model request failed: {exc}") from exc

        if not response.text:
            raise ExtractionError("Model returned an empty response.")
        try:
            return ContractExtraction.model_validate_json(response.text)
        except ValidationError as exc:
            raise ExtractionError("Model output did not match the contract schema.") from exc
