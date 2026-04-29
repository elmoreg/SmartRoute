"""Seed the local DB with synthetic sessions to demo the UI.

Usage:
    python scripts/seed_demo.py [--days 14]
"""
import argparse
import random
from datetime import datetime, timedelta

import httpx


def make_samples(n_minutes: int, restless: bool = False, snorer: bool = False):
    rng = random.Random(0 if not restless else 7)
    samples = []
    for m in range(n_minutes):
        # Cycle through phases: deep early, then mostly light, awake bursts.
        if not restless and m < n_minutes * 0.3:
            motion = rng.uniform(0.0, 0.06)
            noise = rng.uniform(20, 30)
        elif m % 90 < 8:
            motion = rng.uniform(0.4, 0.7)
            noise = rng.uniform(50, 70)
        else:
            motion = rng.uniform(0.05, 0.25)
            noise = rng.uniform(25, 40)
        snoring = snorer and (m % 23 < 4) and motion < 0.2
        samples.append({
            "minute": m,
            "motion": round(motion, 3),
            "noise_db": round(noise, 1),
            "snoring": snoring,
        })
    return samples


def seed(base_url: str, days: int):
    client = httpx.Client(base_url=base_url, timeout=10)
    # Wipe first (best-effort).
    existing = client.get("/api/sessions").json()
    for s in existing:
        client.delete(f"/api/sessions/{s['id']}")

    now = datetime.now()
    for i in range(days):
        night = now - timedelta(days=i)
        started = night.replace(hour=23, minute=15) - timedelta(days=1) if night.hour < 6 else night.replace(hour=23, minute=15)
        duration = random.randint(330, 480)
        ended = started + timedelta(minutes=duration)
        restless = random.random() < 0.25
        snorer = random.random() < 0.6
        samples = make_samples(duration, restless=restless, snorer=snorer)
        r = client.post("/api/sessions", json={
            "started_at": started.isoformat(),
            "ended_at": ended.isoformat(),
            "samples": samples,
        })
        r.raise_for_status()
        d = r.json()
        print(f"  {started:%Y-%m-%d %H:%M}  score={d['quality_score']:5.1f}  deep={d['deep_sleep_min']:4.0f}m  snores={d['snore_events']}")
    print(f"Seeded {days} sessions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    seed(args.url, args.days)
