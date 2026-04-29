import os
import tempfile
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    # Reload modules so they pick up the patched env.
    import importlib
    from app import config, database, main
    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(main)
    database.init_db()
    return TestClient(main.app)


def _payload():
    return {
        "started_at": "2026-04-18T23:00:00",
        "ended_at": "2026-04-19T06:00:00",
        "samples": [
            {"minute": i, "motion": 0.03, "noise_db": 28.0, "snoring": False}
            for i in range(30)
        ],
    }


def test_create_and_get_session(client):
    res = client.post("/api/sessions", json=_payload())
    assert res.status_code == 201
    data = res.json()
    assert data["duration_min"] == 30
    assert data["quality_score"] > 0
    assert len(data["samples"]) == 30
    assert all(s["phase"] == "deep" for s in data["samples"])

    sid = data["id"]
    got = client.get(f"/api/sessions/{sid}")
    assert got.status_code == 200
    assert got.json()["id"] == sid


def test_list_sessions_returns_recent_first(client):
    p1 = _payload()
    p2 = dict(p1)
    p2["started_at"] = "2026-04-19T23:00:00"
    p2["ended_at"] = "2026-04-20T06:00:00"
    client.post("/api/sessions", json=p1)
    client.post("/api/sessions", json=p2)

    res = client.get("/api/sessions")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    assert items[0]["started_at"].startswith("2026-04-19")


def test_delete_session(client):
    res = client.post("/api/sessions", json=_payload())
    sid = res.json()["id"]
    d = client.delete(f"/api/sessions/{sid}")
    assert d.status_code == 204
    g = client.get(f"/api/sessions/{sid}")
    assert g.status_code == 404


def test_pwa_routes(client):
    sw = client.get("/sw.js")
    assert sw.status_code == 200
    assert "javascript" in sw.headers["content-type"]

    mf = client.get("/manifest.webmanifest")
    assert mf.status_code == 200
    assert "manifest" in mf.headers["content-type"]


def test_trends_endpoint(client):
    client.post("/api/sessions", json=_payload())
    res = client.get("/api/sessions/trends?days=7")
    assert res.status_code == 200
    data = res.json()
    assert len(data["days"]) == 7
    assert data["nights_tracked"] >= 0


def test_trends_endpoint_clamps_days(client):
    res = client.get("/api/sessions/trends?days=999")
    assert res.status_code == 200
    assert len(res.json()["days"]) == 60
