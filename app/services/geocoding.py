"""Nominatim geocoding wrapper (free, no API key required)."""
from typing import Any, Dict, Optional

from app.services.google_client import get_client

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

# Fields inspected from the Nominatim ``address`` object to derive the
# delivery "sector".  Order defines priority — first match wins.
SECTOR_ADDRESS_KEYS = (
    "suburb",
    "city_district",
    "town",
    "city",
)


def extract_sector(address: Dict[str, Any]) -> Optional[str]:
    """Pick the most specific neighbourhood/locality from a Nominatim address dict."""
    for key in SECTOR_ADDRESS_KEYS:
        value = address.get(key)
        if value:
            return value
    return None


def parse_nominatim_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a single Nominatim JSON result into the app's canonical shape."""
    address = result.get("address", {})
    return {
        "formatted_address": result.get("display_name", ""),
        "lat": float(result["lat"]),
        "lng": float(result["lon"]),
        "sector": extract_sector(address),
        "place_id": str(result.get("place_id", "")),
    }


async def geocode_address(text: str) -> Optional[Dict[str, Any]]:
    """Resolve a free-text address via Nominatim. Returns None if no results."""
    params = {
        "q": text,
        "format": "json",
        "addressdetails": "1",
        "limit": "1",
    }
    client = get_client()
    response = await client.get(NOMINATIM_SEARCH_URL, params=params)
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    return parse_nominatim_result(results[0])
