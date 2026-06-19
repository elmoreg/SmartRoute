"""Shared httpx client for external API calls (Nominatim, OSRM)."""
import httpx

_client: httpx.AsyncClient | None = None

NOMINATIM_HEADERS = {"User-Agent": "SmartRoute/1.0"}


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=20.0, headers=NOMINATIM_HEADERS)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
