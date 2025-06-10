from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Load settings from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra='ignore')

    # Supabase - Now Optional so you can run the app without them
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None

    # Mistral AI - Still required for the core OCR service
    MISTRAL_API_KEY: str

    # JWT Authentication - Still needed for auth endpoints if you use them
    SECRET_KEY: str = "your-default-secret-key-if-not-in-env"
    ALGORITHM: str = "HS256"

# Create a single, importable instance of the settings
settings = Settings()