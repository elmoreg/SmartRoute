"""Route optimization endpoints."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Address, Route, RouteStop
from app.schemas import AddressOut, OptimizeRequest, RouteOut, RouteStopOut
from app.services.optimizer import optimize_by_distance, optimize_by_sector

router = APIRouter(prefix="/api/routes", tags=["routes"])


def _serialize_route(session: Session, route: Route) -> RouteOut:
    stops = list(
        session.exec(
            select(RouteStop).where(RouteStop.route_id == route.id).order_by(RouteStop.order_index)
        )
    )
    out_stops: List[RouteStopOut] = []
    for stop in stops:
        addr = session.get(Address, stop.address_id)
        if addr is None:
            continue
        out_stops.append(
            RouteStopOut(
                order_index=stop.order_index,
                address=AddressOut.model_validate(addr),
                leg_distance_m=stop.leg_distance_m,
                leg_duration_s=stop.leg_duration_s,
            )
        )
    return RouteOut(
        id=route.id,
        created_at=route.created_at,
        mode=route.mode,
        origin_lat=route.origin_lat,
        origin_lng=route.origin_lng,
        total_distance_m=route.total_distance_m,
        total_duration_s=route.total_duration_s,
        overview_polyline=route.overview_polyline,
        stops=out_stops,
    )


@router.post("/optimize", response_model=RouteOut)
async def optimize(req: OptimizeRequest, session: Session = Depends(get_session)) -> RouteOut:
    if req.mode not in ("distance", "sector"):
        raise HTTPException(status_code=400, detail="mode must be 'distance' or 'sector'")
    if not req.address_ids:
        raise HTTPException(status_code=400, detail="address_ids cannot be empty")

    addresses = [session.get(Address, aid) for aid in req.address_ids]
    addresses = [a for a in addresses if a is not None]
    if not addresses:
        raise HTTPException(status_code=404, detail="No valid addresses found")

    origin = (req.origin.lat, req.origin.lng)
    summary = (
        await optimize_by_distance(origin, addresses)
        if req.mode == "distance"
        else await optimize_by_sector(origin, addresses)
    )

    route = Route(
        mode=req.mode,
        origin_lat=req.origin.lat,
        origin_lng=req.origin.lng,
        total_distance_m=summary["total_distance_m"],
        total_duration_s=summary["total_duration_s"],
        overview_polyline=summary.get("overview_polyline"),
    )
    session.add(route)
    session.commit()
    session.refresh(route)

    legs = summary["legs"]
    for idx, addr_id in enumerate(summary["ordered_address_ids"]):
        leg = legs[idx] if idx < len(legs) else {"distance_m": 0, "duration_s": 0}
        stop = RouteStop(
            route_id=route.id,
            address_id=addr_id,
            order_index=idx,
            leg_distance_m=leg["distance_m"],
            leg_duration_s=leg["duration_s"],
        )
        session.add(stop)
    session.commit()

    return _serialize_route(session, route)


@router.get("", response_model=List[RouteOut])
def list_routes(session: Session = Depends(get_session)) -> List[RouteOut]:
    routes = list(session.exec(select(Route).order_by(Route.created_at.desc())))
    return [_serialize_route(session, r) for r in routes]


@router.get("/{route_id}", response_model=RouteOut)
def get_route(route_id: int, session: Session = Depends(get_session)) -> RouteOut:
    route = session.get(Route, route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    return _serialize_route(session, route)
