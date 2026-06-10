"""Unit tests for the route optimizer.

We mock ``_call_osrm_trip`` and ``_call_osrm_route`` so the tests never hit
OSRM's network.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services import optimizer
from app.services.optimizer import (
    haversine_m,
    optimize_by_distance,
    optimize_by_sector,
    _group_by_sector,
)


def make_addr(id_, lat, lng, sector=None):
    return SimpleNamespace(id=id_, lat=lat, lng=lng, sector=sector)


def fake_trip_response(waypoint_indices, addresses, distance_each=1000, duration_each=60):
    """Build a fake OSRM /trip response.

    ``waypoint_indices`` maps each input coordinate (index 0 = origin) to its
    position in the optimised trip.
    """
    num_legs = len(waypoint_indices) - 1  # legs = waypoints - 1
    return {
        "code": "Ok",
        "waypoints": [
            {"waypoint_index": idx, "location": [0, 0]}
            for idx in waypoint_indices
        ],
        "trips": [
            {
                "geometry": "fake_polyline",
                "legs": [
                    {"distance": distance_each, "duration": duration_each}
                    for _ in range(num_legs)
                ],
            }
        ],
    }


def fake_route_response(distance=1000, duration=60):
    """Build a fake OSRM /route response (single origin→destination)."""
    return {
        "code": "Ok",
        "routes": [
            {
                "geometry": "fake_polyline",
                "legs": [
                    {"distance": distance, "duration": duration}
                ],
            }
        ],
    }


def test_haversine_known_distance():
    # Santiago -> Valparaiso ~ 100 km
    d = haversine_m(-33.45, -70.66, -33.04, -71.62)
    assert 95_000 < d < 115_000


def test_group_by_sector_buckets_addresses():
    addrs = [
        make_addr(1, 0, 0, "A"),
        make_addr(2, 0, 0, "B"),
        make_addr(3, 0, 0, "A"),
        make_addr(4, 0, 0, None),
    ]
    groups = _group_by_sector(addrs)
    assert set(groups.keys()) == {"A", "B", "Sin sector"}
    assert [a.id for a in groups["A"]] == [1, 3]


@pytest.mark.asyncio
async def test_optimize_by_distance_reorders_via_trip():
    addrs = [
        make_addr(10, -33.45, -70.66),
        make_addr(20, -33.46, -70.67),
        make_addr(30, -33.47, -70.68),
        make_addr(40, -33.48, -70.69),
    ]
    # OSRM decides optimal order for 5 waypoints (origin + 4 addresses).
    # waypoint_indices: origin=0, addr10->3, addr20->1, addr30->2, addr40->4
    # Sorted by waypoint_index: origin(0), addr20(1), addr30(2), addr10(3), addr40(4)
    fake = fake_trip_response(
        waypoint_indices=[0, 3, 1, 2, 4],
        addresses=addrs,
        distance_each=1000,
        duration_each=60,
    )

    with patch.object(optimizer, "_call_osrm_trip", new=AsyncMock(return_value=fake)) as m:
        result = await optimize_by_distance((-33.44, -70.65), addrs)

    m.assert_awaited_once()
    # Reordered by waypoint_index (excluding origin at 0):
    # addr20 (index 1), addr30 (index 2), addr10 (index 3), addr40 (index 4)
    assert result["ordered_address_ids"] == [20, 30, 10, 40]
    assert result["total_distance_m"] == 4000
    assert result["total_duration_s"] == 240
    assert result["overview_polyline"] == "fake_polyline"


@pytest.mark.asyncio
async def test_optimize_by_distance_single_address():
    addrs = [make_addr(1, -33.45, -70.66)]
    fake = fake_route_response(distance=1000, duration=60)

    with patch.object(optimizer, "_call_osrm_route", new=AsyncMock(return_value=fake)):
        result = await optimize_by_distance((-33.44, -70.65), addrs)

    assert result["ordered_address_ids"] == [1]
    assert result["total_distance_m"] == 1000


@pytest.mark.asyncio
async def test_optimize_by_distance_empty():
    result = await optimize_by_distance((0, 0), [])
    assert result["ordered_address_ids"] == []
    assert result["total_distance_m"] == 0


@pytest.mark.asyncio
async def test_optimize_by_sector_groups_and_orders_by_proximity():
    # Two sectors. Sector "Near" is right next to the origin, "Far" is far away.
    addrs = [
        make_addr(1, -33.50, -70.70, "Far"),
        make_addr(2, -33.51, -70.71, "Far"),
        make_addr(3, -33.451, -70.661, "Near"),
        make_addr(4, -33.452, -70.662, "Near"),
    ]
    origin = (-33.45, -70.66)

    # For 2-address groups: origin + 2 addresses = 3 waypoints, 2 legs
    fake = fake_trip_response(
        waypoint_indices=[0, 1, 2],
        addresses=[],  # not used directly
        distance_each=500,
        duration_each=30,
    )

    with patch.object(optimizer, "_call_osrm_trip", new=AsyncMock(return_value=fake)) as m:
        result = await optimize_by_sector(origin, addrs)

    # Two sectors -> two calls to OSRM trip.
    assert m.await_count == 2
    # "Near" group must come first.
    assert result["ordered_address_ids"][:2] == [3, 4]
    assert result["ordered_address_ids"][2:] == [1, 2]
    # Totals are sum across both groups (4 legs total).
    assert result["total_distance_m"] == 2000
    assert result["total_duration_s"] == 120


def test_async_runs():
    # Smoke test that pytest-asyncio is wired correctly.
    asyncio.get_event_loop()
