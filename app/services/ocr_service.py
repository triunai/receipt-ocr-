import base64
import json
import time
import re
from mistralai import Mistral
from pydantic import ValidationError
from typing import Dict, Any

from app.core.config import settings
from app.exceptions import OCRError
from app.models.receipt import ParsedDocument

class OcrService:
    def __init__(self):
        self.client = Mistral(api_key=settings.MISTRAL_API_KEY)
        self.parser_model = "mistral-small-latest"  # For parsing OCR text to structured data

    def process_receipt(self, file_content: bytes, mime_type: str) -> ParsedDocument:
        """Process receipt image/PDF using Mistral OCR and parse to structured data."""
        try:
            # Step 1: Extract text using Mistral OCR
            raw_text = self._extract_text_with_ocr(file_content, mime_type)
            
            print(f"🔍 DEBUG: OCR extracted text: {raw_text[:500]}...")  # Show first 500 chars
            
            # Step 2: Parse extracted text to structured data
            structured_data = self._parse_text_to_document(raw_text)
            
            return structured_data
            
        except Exception as e:
            print(f"❌ ERROR: OCR processing failed: {str(e)}")
            raise OCRError(f"OCR processing error: {str(e)}")

    def _extract_text_with_ocr(self, file_content: bytes, mime_type: str) -> str:
        """
        Extract text from file using Mistral's dedicated OCR API.
        This version passes the file content directly as a base64 encoded data URI,
        which is simpler and more direct than the file upload workflow.
        """
        try:
            print(f"🔄 DEBUG: Encoding file and sending to Mistral OCR service...")
            base64_content = base64.b64encode(file_content).decode("utf-8")
            
            document_payload = {}
            if mime_type.startswith("image/"):
                document_payload = {
                    "type": "image_url",
                    "image_url": f"data:{mime_type};base64,{base64_content}",
                }
            elif mime_type == "application/pdf":
                 document_payload = {
                    "type": "document_url",
                    "document_url": f"data:{mime_type};base64,{base64_content}",
                }
            else:
                raise OCRError(f"Unsupported MIME type for OCR: {mime_type}")

            print(f"🔄 DEBUG: Requesting OCR processing for MIME type: {mime_type}...")
            ocr_response = self.client.ocr.process(
                model="mistral-ocr-latest",
                document=document_payload,
                include_image_base64=False # No need to get the image back
            )

            print(f"🔍 DEBUG: OCR response received with {len(ocr_response.pages)} pages")
            
            # Extract text from all pages
            extracted_text = ""
            for page in ocr_response.pages:
                if hasattr(page, 'markdown') and page.markdown:
                    extracted_text += page.markdown + "\n\n"
                elif hasattr(page, 'text') and page.text:
                    extracted_text += page.text + "\n\n"
            
            if not extracted_text.strip():
                raise OCRError("No text extracted from document after successful OCR call.")
                
            print(f"🔍 DEBUG: Extracted text length: {len(extracted_text)} characters")
            print(f"🔍 DEBUG: First 200 chars: {extracted_text[:200]}...")
                
            return extracted_text.strip()
            
        except Exception as e:
            error_msg = f"OCR extraction failed: {str(e)}"
            print(f"❌ DEBUG: {error_msg}")
            raise OCRError(error_msg)

    def _clean_json_response(self, raw_text: str) -> str:
        """Extracts a JSON string from a raw text response that might include markdown."""
        # Find JSON within ```json ... ```
        match = re.search(r'```json\s*(\{.*?\})\s*```', raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)

        # Fallback to finding the first '{' and last '}'
        start = raw_text.find('{')
        end = raw_text.rfind('}')
        if start != -1 and end != -1:
            return raw_text[start:end+1]

        return "" # Return empty if no JSON found

    def _parse_text_to_document(self, text: str, max_retries: int = 3) -> ParsedDocument:
        """Parse text from OCR into a structured ParsedDocument object using an LLM."""
        
        # Truncate text if too long to avoid token limits
        if len(text) > 1000:
            text = text[:1000] + "..."
        
        prompt = f"""You are an expert data extractor. Parse the following document text into a structured JSON format.

Your task is to identify and extract the following fields:
- vendor (string): The name of the store, company, or vendor.
- total (float): The final total amount.
- subtotal (float, optional): The subtotal before taxes or discounts.
- tax_amount (float, optional): The total amount of tax paid.
- currency (string, optional): The currency code (e.g., "MYR", "USD").
- invoice_id (string, optional): The invoice, receipt, or document number.
- order_id (string, optional): The order number, if available.
- purchase_date (string, optional): The date of the transaction in YYYY-MM-DD format.
- purchase_time (string, optional): The time of the transaction in HH:MM:SS format.
- payment_method (string, optional): The method of payment (e.g., "cash", "credit card").
- items (array of objects): A list of purchased items. Each item should have:
  - name (string): The name of the item.
  - quantity (float): The quantity of the item, defaulting to 1.0 if not specified.
  - price (float): The total price for the item line (quantity * unit_price).
  - unit_price (float, optional): The price per unit of the item.
  - description (string, optional): Any additional details about the item.

If a field is not present in the text, omit it from the JSON, unless it has a default value.
Return only the valid JSON object, without any surrounding text or markdown.

Document Text:
---
{text}
---
"""

        for attempt in range(max_retries):
            try:
                response = self.client.chat.complete(
                    model=self.parser_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=500
                )
                
                # The response might be wrapped in markdown or have extra text
                raw_response_content = response.choices[0].message.content
                print(f"🔍 DEBUG: Raw LLM response (attempt {attempt + 1}):\n---\n{raw_response_content}\n---")
                
                # Clean the response to get just the JSON
                json_str = self._clean_json_response(raw_response_content)
                
                if not json_str:
                    print(f"⚠️ DEBUG: No JSON object found in LLM response.")
                    last_error = OCRError("LLM did not return a JSON object.")
                    time.sleep(attempt + 1)
                    continue

                # The response should be a clean JSON string
                parsed_json = json.loads(json_str)
                
                # Validate with Pydantic
                document = ParsedDocument(**parsed_json)
                print(f"✅ DEBUG: Successfully parsed and validated JSON.")
                return document
            except json.JSONDecodeError as e:
                error_details = f"Malformed JSON from LLM: {e}. Raw text: {raw_response_content[:300]}..."
                print(f"❌ DEBUG: {error_details}")
                last_error = OCRError(f"JSON parsing error: {error_details}")
                time.sleep(attempt + 1) # Wait before retrying
            except ValidationError as e:
                error_details = f"LLM output failed validation: {e}. Raw text: {raw_response_content[:300]}..."
                print(f"❌ DEBUG: {error_details}")
                last_error = OCRError(f"LLM output validation error: {error_details}")
                time.sleep(attempt + 1) # Wait before retrying
            except Exception as e:
                if "429" in str(e) or "rate limit" in str(e).lower():
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"⏳ Rate limit hit, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise OCRError(f"Text parsing error: {str(e)}")

        print(f"❌ DEBUG: Failed to parse text into valid JSON after {max_retries} attempts. Returning default document.")
        return ParsedDocument(vendor="Unknown Store", total=0, items=[]) 