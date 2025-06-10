from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from jose import jwt
from datetime import datetime, timedelta

from app.core.config import settings
from app.models.user import UserAuth, Token
from app.api.deps import get_supabase_client

router = APIRouter()

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserAuth,
    supabase: Client = Depends(get_supabase_client)
):
    try:
        res = supabase.auth.sign_up({"email": user_data.email, "password": user_data.password})
        if res.user and res.user.id:
            return {"message": "Signup successful, please verify your email."}
        # Supabase acks the request even if user exists, so this detail is more general
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not sign up user.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=Token)
async def login(
    user_data: UserAuth,
    supabase: Client = Depends(get_supabase_client)
):
    try:
        res = supabase.auth.sign_in_with_password({"email": user_data.email, "password": user_data.password})
        if not res.user or not res.session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        expires_delta = timedelta(minutes=60)
        to_encode = {"sub": str(res.user.id), "exp": datetime.utcnow() + expires_delta}
        token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        return Token(access_token=token, token_type="bearer")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
