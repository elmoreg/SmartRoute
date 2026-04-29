from datetime import datetime, timedelta

from app.models import SleepSession
from app.services.trends import build_trends, _session_date


def make(started_at, **kwargs):
    defaults = dict(
        ended_at=started_at + timedelta(hours=7),
        duration_min=420,
        quality_score=70,
        deep_sleep_min=90,
        light_sleep_min=300,
        awake_min=30,
        snore_events=4,
        snore_total_sec=240,
        avg_noise_db=35,
    )
    defaults.update(kwargs)
    return SleepSession(started_at=started_at, **defaults)


def test_session_started_after_midnight_attributed_to_previous_day():
    s = make(datetime(2026, 4, 19, 2, 30))
    assert _session_date(s).isoformat() == "2026-04-18"


def test_session_started_evening_attributed_to_same_day():
    s = make(datetime(2026, 4, 19, 23, 0))
    assert _session_date(s).isoformat() == "2026-04-19"


def test_build_trends_includes_all_days_in_window():
    today = datetime.now()
    sessions = [make(today - timedelta(days=2, hours=2))]
    res = build_trends(sessions, days=7)
    assert len(res.days) == 7
    assert res.nights_tracked == 1


def test_build_trends_aggregates_multiple_per_day():
    today = datetime.now()
    a = make(today.replace(hour=23, minute=0), quality_score=60, snore_events=2)
    b = make(today.replace(hour=22, minute=30), quality_score=80, snore_events=8)
    res = build_trends([a, b], days=3)
    today_iso = today.date().isoformat()
    today_entry = next(d for d in res.days if d.date == today_iso)
    assert today_entry.sessions == 2
    assert today_entry.quality_score == 70.0
    assert today_entry.snore_events == 10


def test_build_trends_excludes_outside_window():
    today = datetime.now()
    old = make(today - timedelta(days=30))
    res = build_trends([old], days=7)
    assert res.nights_tracked == 0
    assert all(d.sessions == 0 for d in res.days)


def test_build_trends_empty_returns_zeros():
    res = build_trends([], days=7)
    assert res.nights_tracked == 0
    assert res.avg_quality == 0
    assert res.avg_deep_min == 0
    assert res.total_snore_events == 0
