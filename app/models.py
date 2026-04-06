"""SQLModel database models."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Address(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    raw_text: str
    formatted_address: str
    lat: float
    lng: float
    sector: Optional[str] = None
    place_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    usage_count: int = 0


class Route(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    mode: str  # "distance" or "sector"
    origin_lat: float
    origin_lng: float
    total_distance_m: int = 0
    total_duration_s: int = 0
    overview_polyline: Optional[str] = None


class RouteStop(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    route_id: int = Field(foreign_key="route.id", index=True)
    address_id: int = Field(foreign_key="address.id")
    order_index: int
    leg_distance_m: int = 0
    leg_duration_s: int = 0
