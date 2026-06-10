"""Unit tests for the Nominatim geocoding helpers."""
from app.services.geocoding import extract_sector, parse_nominatim_result


def test_extract_sector_prefers_suburb():
    address = {
        "suburb": "Providencia",
        "city": "Santiago",
        "state": "Región Metropolitana",
    }
    assert extract_sector(address) == "Providencia"


def test_extract_sector_falls_back_to_city_district():
    address = {
        "city_district": "Las Condes",
        "city": "Santiago",
        "state": "Región Metropolitana",
    }
    assert extract_sector(address) == "Las Condes"


def test_extract_sector_falls_back_to_town():
    address = {
        "town": "Maipú",
        "state": "Región Metropolitana",
    }
    assert extract_sector(address) == "Maipú"


def test_extract_sector_falls_back_to_city():
    address = {
        "city": "Santiago",
        "state": "Región Metropolitana",
    }
    assert extract_sector(address) == "Santiago"


def test_extract_sector_returns_none_when_missing():
    assert extract_sector({}) is None


def test_parse_nominatim_result_full_payload():
    result = {
        "display_name": "Av. Apoquindo 4500, Las Condes, Santiago, Chile",
        "place_id": 123456,
        "lat": "-33.41",
        "lon": "-70.57",
        "address": {
            "road": "Av. Apoquindo",
            "house_number": "4500",
            "suburb": "Las Condes",
            "city": "Santiago",
            "country": "Chile",
        },
    }
    parsed = parse_nominatim_result(result)
    assert parsed == {
        "formatted_address": "Av. Apoquindo 4500, Las Condes, Santiago, Chile",
        "lat": -33.41,
        "lng": -70.57,
        "sector": "Las Condes",
        "place_id": "123456",
    }
