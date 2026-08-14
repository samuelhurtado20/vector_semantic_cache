# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    gemini_api_key: str
    similarity_threshold: float = 0.90
    database_url: str = "sqlite:///./chat_cache.db"
    gemini_model: str = "gemini-flash-latest"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
