import base64
import json
import os
import sys

from dotenv import load_dotenv
from mistralai import Mistral
from pydantic import ValidationError

# Local application imports for better structure
from .config import MISTRAL_OCR_MODEL, MISTRAL_PARSER_MODEL
from .exceptions import MistralOCRError
from .models import ParsedReceipt

load_dotenv()


class MistralOCR:
    def __init__(self):
        self.api_key = os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY is not set in the environment.")
        self.client = Mistral(api_key=self.api_key)

    def _encode_file(self, file_path: str) -> str:
        """Reads a file and returns its Base64 encoded content."""
        try:
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except FileNotFoundError:
            raise MistralOCRError(f"File not found at path: {file_path}")

    def _get_data_uri(self, file_path: str, encoded_content: str) -> tuple[str, str, str]:
        """Determines the data URI and payload info based on file extension."""
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == '.pdf':
            return f"data:application/pdf;base64,{encoded_content}", "document_url", "document_url"
        elif file_extension in ['.png', '.jpeg', '.jpg', '.webp', '.avif']:
            mime_type = f"image/{file_extension.strip('.')}"
            return f"data:{mime_type};base64,{encoded_content}", "image_url", "image_url"
        else:
            raise MistralOCRError(f"Unsupported file type: {file_extension}")

    def _call_ocr_api(self, document_payload: dict) -> str:
        """Calls the Mistral OCR API and returns the extracted markdown text."""
        try:
            ocr_response = self.client.ocr.process(
                model=MISTRAL_OCR_MODEL,
                document=document_payload
            )
            return "\n\n".join(page.markdown for page in ocr_response.pages)
        except Exception as e:
            raise MistralOCRError(f"API Error during OCR processing: {e}")

    def _call_parser_api(self, ocr_text: str) -> str:
        """Calls the Mistral chat completion API to parse text and returns the JSON string."""
        messages = [
            {
                "role": "system",
                "content": "You are a receipt parser. You will be given the markdown text from a receipt or invoice. Extract all items, prices, vendor, total, and date. Respond in JSON format only."
            },
            {"role": "user", "content": ocr_text}
        ]
        try:
            # Reverted to using client.chat.complete and a dictionary for messages
            response = self.client.chat.complete(
                model=MISTRAL_PARSER_MODEL,
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            raise MistralOCRError(f"API Error during data parsing: {e}")


    def process_local_document(self, file_path: str) -> ParsedReceipt:
        """
        Process a local document (image or PDF) using Mistral's OCR and a chat model.
        
        This is the main public method that orchestrates the entire process.
        
        Args:
            file_path: Path to the local file.
            
        Returns:
            A Pydantic model instance of the parsed receipt.
        """
        encoded_content = self._encode_file(file_path)
        data_uri, doc_type, payload_key = self._get_data_uri(file_path, encoded_content)
        
        document_payload = {"type": doc_type, payload_key: data_uri}
        
        # Step 1: Raw text extraction
        ocr_text = self._call_ocr_api(document_payload)
        
        # Step 2: Intelligent data parsing
        json_response_string = self._call_parser_api(ocr_text)

        # Step 3: Validate and structure the data
        try:
            # Pydantic will automatically validate the incoming dictionary
            parsed_data = ParsedReceipt.model_validate_json(json_response_string)
            return parsed_data
        except ValidationError as e:
            # This gives a super clear error about what was wrong with the JSON
            raise MistralOCRError(f"Failed to validate API response: {e}")
        except json.JSONDecodeError:
            raise MistralOCRError(f"Invalid JSON response from Mistral parser: {json_response_string}")


if __name__ == '__main__':
    ocr_processor = MistralOCR()

    if len(sys.argv) > 1:
        local_file_path = sys.argv[1]
    else:
        # Create a placeholder file if none is provided
        placeholder_filename = 'invoice.png'
        if not os.path.exists(placeholder_filename):
            print(f"No file provided. Creating a placeholder: '{placeholder_filename}'")
            print("Please replace this file with your actual invoice or provide a path.")
            # Creating an empty file is enough for a placeholder
            open(placeholder_filename, 'a').close()
        local_file_path = placeholder_filename

    print(f"Processing file: {local_file_path}...")

    try:
        result = ocr_processor.process_local_document(local_file_path)
        print("\n✅ Successfully extracted and validated data:")
        # .model_dump_json() is the pydantic way to get a json string
        print(result.model_dump_json(indent=2))
    except MistralOCRError as e:
        print(f"\n❌ A processing error occurred: {e}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")