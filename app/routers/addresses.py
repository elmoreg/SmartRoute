"""Address endpoints — geocoding and persistence."""
import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Address
from app.schemas import AddressOut, BulkGeocodeRequest, GeocodeRequest
from app.services.geocoding import geocode_address

router = APIRouter(prefix="/api/addresses", tags=["addresses"])


def _upsert_address(session: Session, raw_text: str, geocoded: dict) -> Address:
    statement = select(Address).where(Address.place_id == geocoded["place_id"])
    existing = session.exec(statement).first()
    if existing is not None:
        existing.usage_count += 1
        existing.formatted_address = geocoded["formatted_address"]
        existing.lat = geocoded["lat"]
        existing.lng = geocoded["lng"]
        existing.sector = geocoded["sector"]
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    address = Address(
        raw_text=raw_text,
        formatted_address=geocoded["formatted_address"],
        lat=geocoded["lat"],
        lng=geocoded["lng"],
        sector=geocoded["sector"],
        place_id=geocoded["place_id"],
        usage_count=1,
    )
    session.add(address)
    session.commit()
    session.refresh(address)
    return address


@router.post("/geocode", response_model=AddressOut)
async def geocode(req: GeocodeRequest, session: Session = Depends(get_session)) -> Address:
    geocoded = await geocode_address(req.text)
    if geocoded is None:
        raise HTTPException(status_code=404, detail="Address not found")
    return _upsert_address(session, req.text, geocoded)


@router.post("/bulk", response_model=List[AddressOut])
async def bulk_geocode(
    req: BulkGeocodeRequest, session: Session = Depends(get_session)
) -> List[Address]:
    cleaned = [t.strip() for t in req.texts if t and t.strip()]
    if not cleaned:
        return []
    results = await asyncio.gather(*(geocode_address(t) for t in cleaned), return_exceptions=True)

    addresses: List[Address] = []
    for raw, result in zip(cleaned, results):
        if isinstance(result, Exception) or result is None:
            continue
        addresses.append(_upsert_address(session, raw, result))
    return addresses


@router.get("", response_model=List[AddressOut])
def list_addresses(session: Session = Depends(get_session)) -> List[Address]:
    return list(session.exec(select(Address).order_by(Address.usage_count.desc())))
