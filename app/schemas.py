"""Pydantic request/response schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class GeocodeRequest(BaseModel):
    text: str


class BulkGeocodeRequest(BaseModel):
    texts: List[str]


class AddressOut(BaseModel):
    id: int
    raw_text: str
    formatted_address: str
    lat: float
    lng: float
    sector: Optional[str] = None
    place_id: Optional[str] = None

    class Config:
        from_attributes = True


class LatLng(BaseModel):
    lat: float
    lng: float


class OptimizeRequest(BaseModel):
    origin: LatLng
    address_ids: List[int] = Field(default_factory=list)
    mode: str  # "distance" or "sector"


class RouteStopOut(BaseModel):
    order_index: int
    address: AddressOut
    leg_distance_m: int
    leg_duration_s: int


class RouteOut(BaseModel):
    id: int
    created_at: datetime
    mode: str
    origin_lat: float
    origin_lng: float
    total_distance_m: int
    total_duration_s: int
    overview_polyline: Optional[str] = None
    stops: List[RouteStopOut] = Field(default_factory=list)
