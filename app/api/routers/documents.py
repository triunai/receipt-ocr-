from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from app.services.ocr_service import OcrService
from app.models.receipt import ParsedDocument
from app.exceptions import OCRError
from app.api.deps import get_ocr_service

router = APIRouter()

@router.post("/upload", response_model=ParsedDocument)
async def upload_receipt(
    file: UploadFile = File(...),
    # Temporarily removed user authentication for easier testing
    ocr_service: OcrService = Depends(get_ocr_service)
):
    """Uploads a document, processes it, and returns structured data."""
    try:
        content = await file.read()
        result = ocr_service.process_receipt(file_content=content, mime_type=file.content_type)
        # Placeholder for saving the result to a database
        print(f"Document processed successfully: {result.vendor}")
        return result
    except OCRError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing error: {e.message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        ) 