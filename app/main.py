from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.main import api_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="Receipt OCR API",
        description="API for processing and managing receipts.",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3001", "http://localhost:3000"], # Common frontend ports
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/", tags=["Root"])
    async def root():
        return {"message": "Receipt OCR API is running!", "docs": "/docs", "health": "/health"}

    @app.get("/health", tags=["Health Check"])
    async def health_check():
        return {"status": "healthy"}

    return app

app = create_app() 