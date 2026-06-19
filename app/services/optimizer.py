"""Route optimization services using OSRM (free, no API key required).

Two strategies are exposed:

* ``optimize_by_distance`` — uses OSRM's ``/trip`` endpoint which solves the
  Travelling Salesman Problem and returns the optimal visiting order.
* ``optimize_by_sector`` — groups addresses by their ``sector`` field, sorts
  groups by haversine distance from the origin to the group centroid, then
  optimizes each group sequentially using the trip endpoint.

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

from app.models import Address
from app.services.google_client import get_client

OSRM_TRIP_URL = "https://router.project-osrm.org/trip/v1/driving"
OSRM_ROUTE_URL = "https://router.project-osrm.org/route/v1/driving"


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in meters."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _build_coords_string(
    origin: tuple[float, float],
    addresses: Sequence[Address],
) -> str:
    """Build ``lng,lat;lng,lat;...`` string for OSRM (note: OSRM uses lng,lat order)."""
    parts = [f"{origin[1]},{origin[0]}"]
    for a in addresses:
        parts.append(f"{a.lng},{a.lat}")
    return ";".join(parts)


async def _call_osrm_trip(
    origin: tuple[float, float],
    addresses: Sequence[Address],
) -> Dict[str, Any]:
    """Call OSRM /trip endpoint for TSP solving."""
    coords = _build_coords_string(origin, addresses)
    url = f"{OSRM_TRIP_URL}/{coords}"
    params = {
        "source": "first",
        "roundtrip": "false",
        "geometries": "polyline",
        "overview": "full",
        "steps": "false",
    }
    client = get_client()
    response = await client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "Ok":
        raise RuntimeError(f"OSRM trip error: {payload.get('code')} - {payload.get('message', '')}")
    return payload


async def _call_osrm_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> Dict[str, Any]:
    """Call OSRM /route endpoint for a single origin→destination route."""
    coords = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    url = f"{OSRM_ROUTE_URL}/{coords}"
    params = {
        "geometries": "polyline",
        "overview": "full",
        "steps": "false",
    }
    client = get_client()
    response = await client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "Ok":
        raise RuntimeError(f"OSRM route error: {payload.get('code')} - {payload.get('message', '')}")
    return payload


def _summarize_trip(trip: Dict[str, Any], addresses: Sequence[Address]) -> Dict[str, Any]:
    """Extract ordered IDs, legs, and polyline from an OSRM trip response.

    OSRM ``/trip`` returns ``trips[0].waypoints`` with an ``waypoint_index``
    that describes the optimal order.  Waypoint 0 is the origin (not an
    address), so address indices start at 1.
    """
    waypoints = trip["waypoints"]
    # waypoints[0] is the origin; remaining are addresses in their original
    # order.  Each waypoint has a ``waypoint_index`` telling the position in
    # the optimised trip.
    # Build a list of (optimised_position, address) pairs, excluding origin.
    address_waypoints = []
    for i, wp in enumerate(waypoints):
        if i == 0:
            continue  # skip origin
        address_waypoints.append((wp["waypoint_index"], addresses[i - 1]))

    # Sort by the optimised trip position.
    address_waypoints.sort(key=lambda x: x[0])
    ordered_ids = [addr.id for _, addr in address_waypoints]

    trip_data = trip["trips"][0]
    legs = trip_data.get("legs", [])
    parsed_legs = [
        {
            "distance_m": int(leg.get("distance", 0)),
            "duration_s": int(leg.get("duration", 0)),
        }
        for leg in legs
    ]

    return {
        "ordered_address_ids": ordered_ids,
        "legs": parsed_legs,
        "total_distance_m": sum(l["distance_m"] for l in parsed_legs),
        "total_duration_s": sum(l["duration_s"] for l in parsed_legs),
        "overview_polyline": trip_data.get("geometry"),
    }


async def optimize_by_distance(
    origin: tuple[float, float],
    addresses: List[Address],
) -> Dict[str, Any]:
    """Optimize ordering using OSRM's trip endpoint (TSP solver)."""
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
        payload = await _call_osrm_route(origin, (only.lat, only.lng))
        route = payload["routes"][0]
        legs = route.get("legs", [])
        parsed_legs = [
            {
                "distance_m": int(leg.get("distance", 0)),
                "duration_s": int(leg.get("duration", 0)),
            }
            for leg in legs
        ]
        return {
            "ordered_address_ids": [only.id],
            "legs": parsed_legs,
            "total_distance_m": sum(l["distance_m"] for l in parsed_legs),
            "total_duration_s": sum(l["duration_s"] for l in parsed_legs),
            "overview_polyline": route.get("geometry"),
        }

    payload = await _call_osrm_trip(origin, addresses)
    return _summarize_trip(payload, addresses)


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
        "overview_polyline": polylines[0] if polylines else None,
    }
