from fastapi import FastAPI, UploadFile, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from dotenv import load_dotenv
from supabase import create_client
from .mistral_ocr import MistralOCR
import os

load_dotenv()

app = FastAPI()

# Add CORS middleware with more permissive settings for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # Frontend port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")  # Fallback for development
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("Missing Supabase configuration. Check your .env file.")

supabase = create_client(supabase_url, supabase_key)
ocr_processor = MistralOCR()

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

@app.post("/api/signup")
async def signup(email: str, password: str):
    try:
        user = supabase.auth.sign_up({"email": email, "password": password})
        return {"message": "Signup successful", "user_id": user.user.id}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(e)}
        )

@app.post("/api/login")
async def login(email: str, password: str):
    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        token = jwt.encode({"sub": user.user.id}, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid credentials"}
        )

@app.post("/api/upload-receipt")
async def upload_receipt(
    file: UploadFile,
    user_id: str = Depends(get_current_user)
):
    try:
        # Upload to Supabase Storage
        file_content = await file.read()
        res = supabase.storage.from_("receipts").upload(
            path=f"{user_id}/{file.filename}",
            file=file_content
        )
        
        image_url = supabase.storage.from_("receipts").get_public_url(res.path)
        
        # Process with OCR
        ocr_result = ocr_processor.process_receipt(image_url, user_id)
        
        return {
            "status": "success",
            "message": "Receipt uploaded and processed",
            "image_url": image_url,
            "ocr_result": ocr_result
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": str(e)}
        )