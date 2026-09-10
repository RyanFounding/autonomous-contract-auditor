import fitz  # PyMuPDF
import os
from google import genai
from google.genai import types
from src.schemas import ContractExtraction

def extract_contract_from_pdf(pdf_path: str) -> ContractExtraction:
    """
    Ingests a raw PDF contract, extracts its text layer, and uses Gemini 
    with structured outputs to map it precisely to the ContractExtraction schema.
    """
    # 1. Extract text from PDF using PyMuPDF
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
        
    if not full_text.strip():
        raise ValueError(f"The PDF at {pdf_path} contains no readable text layer.")

    # 2. Initialize the Google GenAI client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
    client = genai.Client(api_key=api_key)

    # 3. Call Gemini 2.5 Flash with strict Pydantic schema enforcement
    prompt = f"""
    Analyze the following legal contract text and extract the required fields accurately.
    
    Contract Text:
    {full_text}
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ContractExtraction,
            temperature=0.0  # Zero temperature ensures deterministic, non-creative extraction
        ),
    )

    # 4. Validate and parse the JSON string back into our strict Pydantic model
    return ContractExtraction.model_validate_json(response.text)