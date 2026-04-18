from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import SleepSession, SleepSample
from ..schemas import SessionCreate, SessionSummary, SessionDetail, SampleOut
from ..services.analyzer import Sample, analyze

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _to_summary(sleep: SleepSession) -> SessionSummary:
    return SessionSummary(
        id=sleep.id,
        started_at=sleep.started_at,
        ended_at=sleep.ended_at,
        duration_min=sleep.duration_min,
        quality_score=sleep.quality_score,
        deep_sleep_min=sleep.deep_sleep_min,
        light_sleep_min=sleep.light_sleep_min,
        awake_min=sleep.awake_min,
        snore_events=sleep.snore_events,
        snore_total_sec=sleep.snore_total_sec,
        avg_noise_db=sleep.avg_noise_db,
        notes=sleep.notes,
    )


def _to_detail(sleep: SleepSession, samples: List[SampleOut]) -> SessionDetail:
    return SessionDetail(**_to_summary(sleep).model_dump(), samples=samples)


@router.post("", response_model=SessionDetail, status_code=201)
def create_session(payload: SessionCreate, db: Session = Depends(get_session)):
    samples = [Sample(minute=s.minute, motion=s.motion, noise_db=s.noise_db, snoring=s.snoring) for s in payload.samples]
    phases, summary = analyze(samples)

    sleep = SleepSession(
        started_at=payload.started_at,
        ended_at=payload.ended_at,
        notes=payload.notes,
        **summary,
    )
    db.add(sleep)
    db.commit()
    db.refresh(sleep)

    for s, ph in zip(payload.samples, phases):
        db.add(SleepSample(
            session_id=sleep.id,
            minute=s.minute,
            phase=ph,
            motion=s.motion,
            noise_db=s.noise_db,
            snoring=s.snoring,
        ))
    db.commit()

    out_samples = [
        SampleOut(minute=s.minute, phase=ph, motion=s.motion, noise_db=s.noise_db, snoring=s.snoring)
        for s, ph in zip(payload.samples, phases)
    ]
    return _to_detail(sleep, out_samples)


@router.get("", response_model=List[SessionSummary])
def list_sessions(db: Session = Depends(get_session)):
    rows = db.exec(select(SleepSession).order_by(SleepSession.started_at.desc())).all()
    return [_to_summary(r) for r in rows]


@router.get("/{session_id}", response_model=SessionDetail)
def get_session_detail(session_id: int, db: Session = Depends(get_session)):
    sleep = db.get(SleepSession, session_id)
    if not sleep:
        raise HTTPException(404, "Session not found")
    rows = db.exec(
        select(SleepSample).where(SleepSample.session_id == session_id).order_by(SleepSample.minute)
    ).all()
    samples = [SampleOut(minute=s.minute, phase=s.phase, motion=s.motion, noise_db=s.noise_db, snoring=s.snoring) for s in rows]
    return _to_detail(sleep, samples)


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_session)):
    sleep = db.get(SleepSession, session_id)
    if not sleep:
        raise HTTPException(404, "Session not found")
    rows = db.exec(select(SleepSample).where(SleepSample.session_id == session_id)).all()
    for s in rows:
        db.delete(s)
    db.delete(sleep)
    db.commit()
