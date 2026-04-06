"""Route optimization services.

Two strategies are exposed:

* ``optimize_by_distance`` — sends every address as a Directions API waypoint
  with ``optimize:true`` so Google itself returns the optimal visiting order.
* ``optimize_by_sector`` — groups addresses by their ``sector`` field, sorts
  groups by haversine distance from the origin to the group centroid, then
  optimizes each group sequentially using Directions API.

Both strategies return the same shape::

    {
        "ordered_address_ids": [int, ...],
        "legs": [{"distance_m": int, "duration_s": int}, ...],
        "total_distance_m": int,
        "total_duration_s": int,
        "overview_polyline": str | None,
    }
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Sequence

from app.config import get_settings
from app.models import Address
from app.services.google_client import get_client

DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in meters."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


async def _call_directions(
    origin: tuple[float, float],
    destination: tuple[float, float],
    waypoints: Sequence[tuple[float, float]],
    optimize: bool = True,
) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.google_maps_api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not configured")

    params: dict[str, str] = {
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{destination[0]},{destination[1]}",
        "key": settings.google_maps_api_key,
        "mode": "driving",
    }
    if waypoints:
        prefix = "optimize:true|" if optimize else ""
        params["waypoints"] = prefix + "|".join(f"{lat},{lng}" for lat, lng in waypoints)

    client = get_client()
    response = await client.get(DIRECTIONS_URL, params=params)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "OK" or not payload.get("routes"):
        raise RuntimeError(f"Directions API error: {payload.get('status')}")
    return payload["routes"][0]


def _summarize_route(route: Dict[str, Any]) -> Dict[str, Any]:
    legs = route.get("legs", [])
    parsed_legs = [
        {
            "distance_m": leg.get("distance", {}).get("value", 0),
            "duration_s": leg.get("duration", {}).get("value", 0),
        }
        for leg in legs
    ]
    return {
        "legs": parsed_legs,
        "total_distance_m": sum(l["distance_m"] for l in parsed_legs),
        "total_duration_s": sum(l["duration_s"] for l in parsed_legs),
        "overview_polyline": (route.get("overview_polyline") or {}).get("points"),
    }


async def optimize_by_distance(
    origin: tuple[float, float],
    addresses: List[Address],
) -> Dict[str, Any]:
    """Optimize ordering using Google's waypoint optimization.

    Destination is set to the *last* address in the optimized order — Google
    decides which one to use because every address is provided as an
    optimizable waypoint and we treat the route as origin → all stops.
    """
    if not addresses:
        return {
            "ordered_address_ids": [],
            "legs": [],
            "total_distance_m": 0,
            "total_duration_s": 0,
            "overview_polyline": None,
        }

    if len(addresses) == 1:
        only = addresses[0]
        route = await _call_directions(origin, (only.lat, only.lng), [], optimize=False)
        summary = _summarize_route(route)
        summary["ordered_address_ids"] = [only.id]
        return summary

    # Use the first address as the destination and let Google optimize the rest.
    destination_addr = addresses[-1]
    waypoint_addrs = addresses[:-1]
    waypoints = [(a.lat, a.lng) for a in waypoint_addrs]
    route = await _call_directions(
        origin,
        (destination_addr.lat, destination_addr.lng),
        waypoints,
        optimize=True,
    )
    waypoint_order = route.get("waypoint_order", list(range(len(waypoints))))
    ordered_ids = [waypoint_addrs[i].id for i in waypoint_order]
    ordered_ids.append(destination_addr.id)

    summary = _summarize_route(route)
    summary["ordered_address_ids"] = ordered_ids
    return summary


def _group_by_sector(addresses: Iterable[Address]) -> Dict[str, List[Address]]:
    groups: Dict[str, List[Address]] = {}
    for addr in addresses:
        key = addr.sector or "Sin sector"
        groups.setdefault(key, []).append(addr)
    return groups


def _centroid(addresses: Sequence[Address]) -> tuple[float, float]:
    n = len(addresses)
    return (sum(a.lat for a in addresses) / n, sum(a.lng for a in addresses) / n)


async def optimize_by_sector(
    origin: tuple[float, float],
    addresses: List[Address],
) -> Dict[str, Any]:
    """Group by sector, order groups by distance, then optimize within each."""
    if not addresses:
        return {
            "ordered_address_ids": [],
            "legs": [],
            "total_distance_m": 0,
            "total_duration_s": 0,
            "overview_polyline": None,
        }

    groups = _group_by_sector(addresses)
    sorted_sectors = sorted(
        groups.keys(),
        key=lambda s: haversine_m(origin[0], origin[1], *_centroid(groups[s])),
    )

    ordered_ids: List[int] = []
    legs: List[Dict[str, int]] = []
    total_distance_m = 0
    total_duration_s = 0
    polylines: list[str] = []

    current_origin = origin
    for sector in sorted_sectors:
        sub_summary = await optimize_by_distance(current_origin, groups[sector])
        ordered_ids.extend(sub_summary["ordered_address_ids"])
        legs.extend(sub_summary["legs"])
        total_distance_m += sub_summary["total_distance_m"]
        total_duration_s += sub_summary["total_duration_s"]
        if sub_summary.get("overview_polyline"):
            polylines.append(sub_summary["overview_polyline"])
        # Next sub-route starts where this one ended.
        last_addr = next(a for a in groups[sector] if a.id == sub_summary["ordered_address_ids"][-1])
        current_origin = (last_addr.lat, last_addr.lng)

    return {
        "ordered_address_ids": ordered_ids,
        "legs": legs,
        "total_distance_m": total_distance_m,
        "total_duration_s": total_duration_s,
        # We keep only the first polyline as a hint; frontend will ask the
        # browser DirectionsService for the full drawing anyway.
        "overview_polyline": polylines[0] if polylines else None,
    }
