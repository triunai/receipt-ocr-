from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from supabase import create_client, Client
from typing import Optional

from app.core.config import settings
from app.services.ocr_service import OcrService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_supabase_client() -> Client:
    # This dependency will now only fail if an endpoint that needs it is called
    # without the proper configuration, instead of crashing on startup.
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured. Please set SUPABASE_URL and SUPABASE_KEY to use this feature."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def get_ocr_service() -> OcrService:
    # ... existing code ...
