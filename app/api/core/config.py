from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Load settings from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Mistral AI
    MISTRAL_API_KEY: str
    MISTRAL_OCR_MODEL: str = "mistral-ocr-latest"
    MISTRAL_PARSER_MODEL: str = "mistral-large-latest"

    # JWT Authentication
    SECRET_KEY: str = "your-default-secret-key-if-not-in-env"
    ALGORITHM: str = "HS256"

# Create a single, importable instance of the settings
settings = Settings()