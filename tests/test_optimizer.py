"""Unit tests for the route optimizer.

We mock ``_call_directions`` so the tests never hit Google's network.
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


def fake_route(waypoint_order, leg_count, distance_each=1000, duration_each=60):
    return {
        "waypoint_order": waypoint_order,
        "legs": [
            {"distance": {"value": distance_each}, "duration": {"value": duration_each}}
            for _ in range(leg_count)
        ],
        "overview_polyline": {"points": "fake_polyline"},
    }


def test_haversine_known_distance():
    # Santiago → Valparaíso ≈ 100 km
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
async def test_optimize_by_distance_reorders_via_waypoint_order():
    addrs = [
        make_addr(10, -33.45, -70.66),
        make_addr(20, -33.46, -70.67),
        make_addr(30, -33.47, -70.68),
        make_addr(40, -33.48, -70.69),
    ]
    # Google decides order: 2nd waypoint first, then 0th, then 1st.
    # waypoints are addrs[:-1] (ids 10,20,30); destination is id 40.
    fake = fake_route(waypoint_order=[2, 0, 1], leg_count=4)

    with patch.object(optimizer, "_call_directions", new=AsyncMock(return_value=fake)) as m:
        result = await optimize_by_distance((-33.44, -70.65), addrs)

    m.assert_awaited_once()
    # Reordered waypoints: id 30, 10, 20, then destination 40.
    assert result["ordered_address_ids"] == [30, 10, 20, 40]
    assert result["total_distance_m"] == 4000
    assert result["total_duration_s"] == 240
    assert result["overview_polyline"] == "fake_polyline"


@pytest.mark.asyncio
async def test_optimize_by_distance_single_address():
    addrs = [make_addr(1, -33.45, -70.66)]
    fake = fake_route(waypoint_order=[], leg_count=1)
    with patch.object(optimizer, "_call_directions", new=AsyncMock(return_value=fake)):
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

    # Each sub-call returns a route with no reordering (waypoint_order=[0]),
    # one waypoint and the destination → 2 legs.
    fake = fake_route(waypoint_order=[0], leg_count=2, distance_each=500, duration_each=30)

    with patch.object(optimizer, "_call_directions", new=AsyncMock(return_value=fake)) as m:
        result = await optimize_by_sector(origin, addrs)

    # Two sectors → two calls to Directions.
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
