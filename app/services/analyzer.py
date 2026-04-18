"""Sleep analysis: phase classification and quality score.

Uses an actigraphy-inspired heuristic:
- motion is a normalized 0..1 magnitude of device acceleration variance in the minute.
- noise_db is a relative dB value (0..100) from audio RMS.
- snoring is a bool flag emitted when low-frequency energy dominates.

Phases:
- awake  : motion > 0.45 OR noise_db > 65
- deep   : motion < 0.08 AND not snoring (sustained stillness)
- light  : everything else
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple


@dataclass
class Sample:
    minute: int
    motion: float
    noise_db: float
    snoring: bool


def classify_phase(s: Sample) -> str:
    if s.motion > 0.45 or s.noise_db > 65:
        return "awake"
    if s.motion < 0.08 and not s.snoring:
        return "deep"
    return "light"


def smooth_phases(phases: List[str], window: int = 3) -> List[str]:
    """Majority-vote smoothing to avoid 1-minute spikes between phases."""
    if window < 2 or not phases:
        return list(phases)
    out: List[str] = []
    half = window // 2
    for i in range(len(phases)):
        lo = max(0, i - half)
        hi = min(len(phases), i + half + 1)
        chunk = phases[lo:hi]
        out.append(max(set(chunk), key=chunk.count))
    return out


def analyze(samples: Iterable[Sample]) -> Tuple[List[str], dict]:
    xs = list(samples)
    if not xs:
        return [], {
            "duration_min": 0.0,
            "quality_score": 0.0,
            "deep_sleep_min": 0.0,
            "light_sleep_min": 0.0,
            "awake_min": 0.0,
            "snore_events": 0,
            "snore_total_sec": 0.0,
            "avg_noise_db": 0.0,
        }

    phases = smooth_phases([classify_phase(s) for s in xs])

    deep = sum(1 for p in phases if p == "deep")
    light = sum(1 for p in phases if p == "light")
    awake = sum(1 for p in phases if p == "awake")
    total = len(phases)

    snore_minutes = sum(1 for s in xs if s.snoring)
    snore_events = 0
    prev = False
    for s in xs:
        if s.snoring and not prev:
            snore_events += 1
        prev = s.snoring

    avg_noise = sum(s.noise_db for s in xs) / total

    # Quality: weighted composition of sleep efficiency + deep sleep ratio,
    # penalized by snoring and noise. Output in 0..100.
    efficiency = (deep + light) / total
    deep_ratio = deep / total
    snore_ratio = snore_minutes / total
    noise_pen = min(1.0, max(0.0, (avg_noise - 35) / 50))
    score = 100 * (0.55 * efficiency + 0.35 * min(1.0, deep_ratio / 0.25))
    score -= 25 * snore_ratio
    score -= 15 * noise_pen
    score = max(0.0, min(100.0, score))

    summary = {
        "duration_min": float(total),
        "quality_score": round(score, 1),
        "deep_sleep_min": float(deep),
        "light_sleep_min": float(light),
        "awake_min": float(awake),
        "snore_events": snore_events,
        "snore_total_sec": float(snore_minutes * 60),
        "avg_noise_db": round(avg_noise, 1),
    }
    return phases, summary
