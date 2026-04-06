"""Unit tests for the geocoding helpers."""
from app.services.geocoding import extract_sector, parse_geocode_result


def test_extract_sector_prefers_sublocality():
    components = [
        {"long_name": "Providencia", "types": ["sublocality_level_1", "political"]},
        {"long_name": "Santiago", "types": ["administrative_area_level_2"]},
        {"long_name": "Región Metropolitana", "types": ["administrative_area_level_1"]},
    ]
    assert extract_sector(components) == "Providencia"


def test_extract_sector_falls_back_to_locality():
    components = [
        {"long_name": "Las Condes", "types": ["locality", "political"]},
        {"long_name": "Región Metropolitana", "types": ["administrative_area_level_1"]},
    ]
    assert extract_sector(components) == "Las Condes"


def test_extract_sector_returns_none_when_missing():
    assert extract_sector([]) is None


def test_parse_geocode_result_full_payload():
    result = {
        "formatted_address": "Av. Apoquindo 4500, Las Condes, Chile",
        "place_id": "ChIJxxx",
        "geometry": {"location": {"lat": -33.41, "lng": -70.57}},
        "address_components": [
            {"long_name": "Las Condes", "types": ["locality"]},
        ],
    }
    parsed = parse_geocode_result(result)
    assert parsed == {
        "formatted_address": "Av. Apoquindo 4500, Las Condes, Chile",
        "lat": -33.41,
        "lng": -70.57,
        "sector": "Las Condes",
        "place_id": "ChIJxxx",
    }
