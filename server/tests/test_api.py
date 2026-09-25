import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from frontdoor.main import create_app

ROOT = Path(__file__).resolve().parents[2]
REPORT = json.loads((ROOT / "evals/specialist.json").read_text())


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path / "test.db", live_enabled=False)


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


def test_default_recording_and_inputs_are_public(client):
    state = client.get("/api/state").json()
    assert len(state["messages"]) == 12
    assert not state["config"]["live_enabled"]
    assert all("expected" not in r["message"] for r in state["messages"])
    assert (
        client.get("/api/evaluation/base/export").json()["summary"]
        == json.loads((ROOT / "evals/base.json").read_text())["summary"]
    )
    assert client.get("/api/evaluation/unknown/export").status_code == 422


@pytest.mark.asyncio
async def test_review_preserves_prediction_and_persists(app):
    screened = await app.state.screen("D02", "recorded")
    assert screened["status"] == "screened"
    with TestClient(app) as client:
        response = client.post(
            "/api/messages/D02/review", json={"label": "legitimate", "note": "My correction"}
        )
        assert response.status_code == 200
        assert response.json()["prediction"] == screened["prediction"]
        export = client.get("/api/export/reviews").json()["examples"]
        assert len(export) == 1
        assert export[0]["label"] == "legitimate"
        assert export[0]["source_fingerprint"] == screened["fingerprint"]
        assert (
            client.get("/api/messages/D02/export").json()["raw_response"]
            == screened["raw_response"]
        )
    recreated = create_app(app.state.store.path, live_enabled=False)
    assert recreated.state.store.get("D02")["review"]["note"] == "My correction"


def test_live_requires_opt_in_and_review_requires_prediction(client):
    assert client.post("/api/run", json={"mode": "live"}).status_code == 403
    assert client.post("/api/variants", json={"message": {"body": "New text"}}).status_code == 403
    assert client.post("/api/messages/D01/review", json={"label": "spam"}).status_code == 409
    assert client.post("/api/messages/unknown/review", json={"label": "spam"}).status_code == 404
    assert client.post("/api/messages/D01/review", json={"label": "custom"}).status_code == 422


@pytest.mark.asyncio
async def test_recording_never_substitutes_for_edited_text(app):
    row = app.state.store.get("D01")
    app.state.store.update("D01", message={**row["message"], "body": "new message"})
    result = await app.state.screen("D01", "recorded")
    assert result["status"] == "error"
    assert result["prediction"] is None
    assert "No recording" in result["error"]


@pytest.mark.asyncio
async def test_live_failure_is_stored_without_fallback(tmp_path, monkeypatch):
    transport = httpx.MockTransport(lambda _: httpx.Response(503))
    original = httpx.AsyncClient
    monkeypatch.setattr(
        "frontdoor.main.httpx.AsyncClient", lambda **kw: original(transport=transport, **kw)
    )
    app = create_app(tmp_path / "failure.db", live_enabled=True)
    result = await app.state.screen("D01", "live")
    assert result["status"] == "error"
    assert result["prediction"] is None
    assert "No prediction was substituted" in result["error"]


def test_fresh_variants_are_sent_to_worker_and_grouped(tmp_path, monkeypatch):
    payloads = []
    saved = next(r for r in REPORT["rows"] if r["case_id"] == "D01")

    def handler(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"result": saved["raw_response"], "model_ms": 42, "metadata": REPORT["metadata"]},
        )

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient
    monkeypatch.setattr(
        "frontdoor.main.httpx.AsyncClient", lambda **kw: original(transport=transport, **kw)
    )
    app = create_app(tmp_path / "variants.db", live_enabled=True)
    with TestClient(app) as client:
        first = client.post(
            "/api/variants", json={"message": {"body": "New one"}, "parent_id": "D01"}
        ).json()
        second = client.post(
            "/api/variants", json={"message": {"body": "New two"}, "parent_id": first["id"]}
        ).json()
        assert len(payloads) == 2
        assert payloads[1]["state"]["body"] == "New two"
        assert second["mode"] == "live"
        assert second["fingerprint"] != first["fingerprint"]
        client.post(f"/api/messages/{second['id']}/review", json={"label": "legitimate"})
        assert client.get("/api/export/reviews").json()["examples"][0]["group"] == "D01"
        assert client.post("/api/variants", json={"message": {"body": "   "}}).status_code == 422
        assert (
            client.post("/api/variants", json={"message": {"body": "x" * 1801}}).status_code == 422
        )


def test_cross_origin_writes_rejected(client):
    assert (
        client.post(
            "/api/run", json={}, headers={"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )
    assert client.get("/api/health").headers["x-content-type-options"] == "nosniff"


def test_interrupted_inference_is_recoverable(tmp_path):
    app = create_app(tmp_path / "restart.db", live_enabled=False)
    app.state.store.update("D01", status="screening")
    restarted = create_app(app.state.store.path, live_enabled=False)
    assert restarted.state.store.get("D01")["status"] == "error"


@pytest.mark.asyncio
async def test_evaluation_exposes_all_failures(app):
    with TestClient(app) as client:
        data = client.get("/api/evaluation").json()
        assert len(data["specialist"]["cases"]) == 283
        assert data["specialist"]["summary"]["challenge"]["correct"] == 17
        assert data["specialist"]["summary"]["gates"]["challenge_accuracy"] is False
