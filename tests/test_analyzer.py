from app.services.analyzer import Sample, analyze, classify_phase, smooth_phases


def make(minute, motion=0.1, noise=30, snoring=False):
    return Sample(minute=minute, motion=motion, noise_db=noise, snoring=snoring)


def test_classify_phase_awake_on_high_motion():
    assert classify_phase(make(0, motion=0.8)) == "awake"


def test_classify_phase_awake_on_loud_noise():
    assert classify_phase(make(0, motion=0.05, noise=80)) == "awake"


def test_classify_phase_deep_on_stillness():
    assert classify_phase(make(0, motion=0.05, noise=30, snoring=False)) == "deep"


def test_classify_phase_light_otherwise():
    assert classify_phase(make(0, motion=0.2, noise=40)) == "light"


def test_snoring_prevents_deep_classification():
    assert classify_phase(make(0, motion=0.05, noise=30, snoring=True)) == "light"


def test_smooth_phases_removes_spikes():
    raw = ["deep", "deep", "awake", "deep", "deep"]
    out = smooth_phases(raw, window=3)
    assert out == ["deep", "deep", "deep", "deep", "deep"]


def test_analyze_empty_returns_zero_summary():
    phases, summary = analyze([])
    assert phases == []
    assert summary["duration_min"] == 0
    assert summary["quality_score"] == 0


def test_analyze_full_deep_night_scores_high():
    samples = [make(i, motion=0.02, noise=25) for i in range(480)]
    phases, summary = analyze(samples)
    assert all(p == "deep" for p in phases)
    assert summary["duration_min"] == 480
    assert summary["deep_sleep_min"] == 480
    assert summary["snore_events"] == 0
    assert summary["quality_score"] >= 85


def test_analyze_counts_snore_events_as_runs():
    # Two separate snore runs -> 2 events, not 4.
    samples = [
        make(0, snoring=True), make(1, snoring=True),
        make(2, snoring=False),
        make(3, snoring=True), make(4, snoring=True),
    ]
    _, summary = analyze(samples)
    assert summary["snore_events"] == 2
    assert summary["snore_total_sec"] == 4 * 60


def test_analyze_noisy_restless_scores_low():
    samples = [make(i, motion=0.7, noise=75, snoring=True) for i in range(60)]
    _, summary = analyze(samples)
    assert summary["quality_score"] < 30
    assert summary["awake_min"] == 60
