from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class SleepSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime
    ended_at: datetime
    duration_min: float
    quality_score: float
    deep_sleep_min: float
    light_sleep_min: float
    awake_min: float
    snore_events: int
    snore_total_sec: float
    avg_noise_db: float
    notes: Optional[str] = None


class SleepSample(SQLModel, table=True):
    """Per-minute sample belonging to a session. Used to reconstruct the hypnogram."""
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sleepsession.id", index=True)
    minute: int
    phase: str  # "awake" | "light" | "deep"
    motion: float
    noise_db: float
    snoring: bool
