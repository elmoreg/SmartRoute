from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class SampleIn(BaseModel):
    minute: int
    motion: float
    noise_db: float
    snoring: bool


class SessionCreate(BaseModel):
    started_at: datetime
    ended_at: datetime
    samples: List[SampleIn]
    notes: Optional[str] = None


class SampleOut(BaseModel):
    minute: int
    phase: str
    motion: float
    noise_db: float
    snoring: bool


class SessionSummary(BaseModel):
    id: int
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


class SessionDetail(SessionSummary):
    samples: List[SampleOut]
