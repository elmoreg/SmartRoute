"""Application configuration loaded from environment variables."""
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    google_maps_api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./smartroute.db")


@lru_cache
def get_settings() -> Settings:
    return Settings()
