class OCRError(Exception):
    """Custom exception for OCR processing errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message) 