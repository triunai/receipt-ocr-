from app.models.receipt import ParsedReceipt
from app.exceptions import OCRError
from app.api.deps import get_ocr_service

router = APIRouter()

@router.post("/upload", response_model=ParsedReceipt)
async def upload_receipt(
    file: UploadFile = File(...),
    ocr_service: OcrService = Depends(get_ocr_service)
):
    try:
        content = await file.read()
        result = ocr_service.process_receipt(file_content=content, mime_type=file.content_type)
        # Placeholder for saving the result to a database
        print(f"Receipt processed successfully: {result.vendor}")
        return result
    except OCRError as e:
