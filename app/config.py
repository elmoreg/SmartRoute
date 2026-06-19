"""Application configuration loaded from environment variables."""
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./smartroute.db")


@lru_cache
def get_settings() -> Settings:
    return Settings()
