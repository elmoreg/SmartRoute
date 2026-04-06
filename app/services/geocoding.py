"""Google Geocoding API wrapper."""
from typing import Any, Dict, Optional

from app.config import get_settings
from app.services.google_client import get_client

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Components inspected to derive the "sector" of a delivery address. Order
# defines the priority — the first match wins.
SECTOR_COMPONENT_PRIORITY = (
    "sublocality_level_1",
    "sublocality",
    "locality",
    "administrative_area_level_3",
    "administrative_area_level_2",
    "neighborhood",
)


def extract_sector(address_components: list[dict[str, Any]]) -> Optional[str]:
    """Pick the most specific neighborhood/locality from a geocoding result."""
    by_type: dict[str, str] = {}
    for component in address_components:
        for t in component.get("types", []):
            by_type.setdefault(t, component.get("long_name", ""))
    for key in SECTOR_COMPONENT_PRIORITY:
        if key in by_type and by_type[key]:
            return by_type[key]
    return None


def parse_geocode_result(result: Dict[str, Any]) -> Dict[str, Any]:
    location = result["geometry"]["location"]
    return {
        "formatted_address": result.get("formatted_address", ""),
        "lat": location["lat"],
        "lng": location["lng"],
        "sector": extract_sector(result.get("address_components", [])),
        "place_id": result.get("place_id"),
    }


async def geocode_address(text: str) -> Optional[Dict[str, Any]]:
    """Resolve a free-text address. Returns None if no results."""
    settings = get_settings()
    if not settings.google_maps_api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not configured")

    params = {"address": text, "key": settings.google_maps_api_key}
    client = get_client()
    response = await client.get(GEOCODE_URL, params=params)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "OK" or not payload.get("results"):
        return None
    return parse_geocode_result(payload["results"][0])
