"""Aggregate sleep sessions into per-day trends."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, List

from ..models import SleepSession
from ..schemas import TrendDay, TrendsResponse


def _session_date(s: SleepSession) -> date:
    """A night that started before 6am is attributed to the previous day."""
    started = s.started_at
    if started.hour < 6:
        return (started - timedelta(days=1)).date()
    return started.date()


def build_trends(sessions: Iterable[SleepSession], days: int = 14) -> TrendsResponse:
    today = datetime.now().date()
    window_start = today - timedelta(days=days - 1)

    by_day: dict[date, List[SleepSession]] = {}
    for s in sessions:
        d = _session_date(s)
        if d < window_start or d > today:
            continue
        by_day.setdefault(d, []).append(s)

    out: List[TrendDay] = []
    for i in range(days):
        d = window_start + timedelta(days=i)
        items = by_day.get(d, [])
        if not items:
            out.append(TrendDay(
                date=d.isoformat(),
                sessions=0,
                duration_min=0.0,
                quality_score=0.0,
                deep_sleep_min=0.0,
                light_sleep_min=0.0,
                awake_min=0.0,
                snore_events=0,
            ))
            continue
        n = len(items)
        out.append(TrendDay(
            date=d.isoformat(),
            sessions=n,
            duration_min=sum(s.duration_min for s in items),
            quality_score=round(sum(s.quality_score for s in items) / n, 1),
            deep_sleep_min=sum(s.deep_sleep_min for s in items),
            light_sleep_min=sum(s.light_sleep_min for s in items),
            awake_min=sum(s.awake_min for s in items),
            snore_events=sum(s.snore_events for s in items),
        ))

    tracked = [d for d in out if d.sessions > 0]
    n = len(tracked)
    return TrendsResponse(
        days=out,
        avg_quality=round(sum(d.quality_score for d in tracked) / n, 1) if n else 0.0,
        avg_duration_min=round(sum(d.duration_min for d in tracked) / n, 1) if n else 0.0,
        avg_deep_min=round(sum(d.deep_sleep_min for d in tracked) / n, 1) if n else 0.0,
        total_snore_events=sum(d.snore_events for d in tracked),
        nights_tracked=n,
    )
