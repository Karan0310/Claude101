from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    claude_model: str = Field(default="claude-sonnet-4-6", env="CLAUDE_MODEL")

    # SerpAPI (Google Jobs)
    serpapi_key: Optional[str] = Field(default=None, env="SERPAPI_KEY")

    # RapidAPI (LinkedIn Jobs)
    rapidapi_key: Optional[str] = Field(default=None, env="RAPIDAPI_KEY")

    # App
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    debug: bool = Field(default=False, env="DEBUG")

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./resume_matcher.db", env="DATABASE_URL")

    # File Upload
    max_upload_size_mb: int = Field(default=10, env="MAX_UPLOAD_SIZE_MB")
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def ensure_upload_dir(self):
        os.makedirs(self.upload_dir, exist_ok=True)


settings = Settings()
settings.ensure_upload_dir()
