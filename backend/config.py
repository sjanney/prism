"""Configuration management for Prism using Pydantic Settings."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


def _get_database_url_from_config() -> str:
    """Get database URL from config file if it exists."""
    config_file = Path.home() / ".prism" / "db_config.ini"
    if config_file.exists():
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(config_file)
            if config.has_section("database") and config.has_option("database", "url"):
                return config.get("database", "url")
        except Exception:
            pass
    return "sqlite+aiosqlite:///prism.db"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and config file."""

    # Database configuration
    # Priority: 1. Environment variable, 2. Config file, 3. Default
    database_url: str = os.getenv("DATABASE_URL") or _get_database_url_from_config()
    
    # CORS configuration
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # CLIP search configuration
    clip_min_similarity: float = 0.25  # Minimum similarity threshold (0-1)
    clip_model_name: str = "openai/clip-vit-base-patch32"
    
    class Config:
        """Pydantic config."""
        
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

