from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Enem da Read"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./src/backend/database.db"
    DATABASE_URL_ASYNC: str = "sqlite+aiosqlite:///./src/backend/database.db"

    # File upload
    MAX_FILE_SIZE_MB: int = 5
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png"]

    # OCR
    TESSERACT_CMD: str = "tesseract"
    OCR_PREPROCESSING_CONTRAST: float = 2.0
    OCR_PREPROCESSING_BRIGHTNESS: float = 1.0
    OCR_TIMEOUT_SECONDS: int = 30

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
