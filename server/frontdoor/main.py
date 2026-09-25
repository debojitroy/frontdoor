import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from frontdoor.engine import decode, fingerprint, prepare, rules
from frontdoor.linear import predict_linear
from frontdoor.store import Store, now

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    channel: Literal["email", "contact form", "community"] = "email"
    sender: str = Field(default="Your test message", max_length=100)
    subject: str = Field(default="", max_length=160)
    body: str = Field(min_length=1, max_length=1800)
    context: str = Field(default="", max_length=500)


class Run(BaseModel):
    mode: Literal["recorded", "live"] = "recorded"


class Variant(BaseModel):
    message: Message
    parent_id: str | None = Field(default=None, max_length=80)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    label: Literal["legitimate", "spam", "phishing"]
    note: str = Field(default="", max_length=1000)


def create_app(database=None, live_enabled=None, worker_url=None):
    db = Store(Path(database or os.getenv("FRONTDOOR_DB", ROOT / "data/frontdoor.db")))
    enabled = (
        os.getenv("FRONTDOOR_ENABLE_LIVE", "false").lower() == "true"
        if live_enabled is None
        else live_enabled
    )
    endpoint = worker_url or os.getenv("FRONTDOOR_WORKER_URL", "http://127.0.0.1:8141")
    fixture = json.loads((ROOT / "fixtures/messages.json").read_text())
    recording = json.loads((ROOT / "evals/specialist.json").read_text())
    base = json.loads((ROOT / "evals/base.json").read_text())
    linear = json.loads((ROOT / "models/spam-linear.json").read_text())
    replay = {r["fingerprint"]: r for r in recording["rows"] if r["dataset"] == "showcase"}
    job = {"running": False, "completed": 0, "total": 0, "mode": "recorded"}
    lock = asyncio.Lock()
    tasks = set()
    if not db.all():
        for case in fixture:
            db.insert(case["id"], Message(**case["message"]).model_dump())
    # A restart must not leave interrupted requests looking as though they are still running.
    for row in db.all():
        if row["status"] == "screening":
            db.update(
                row["id"], status="error", error="Screening was interrupted. Retry this message."
            )

    @asynccontextmanager
    async def lifespan(app):
        yield
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(title="FrontDoor", lifespan=lifespan)
    app.state.store = db
    app.state.live_enabled = enabled

    @app.middleware("http")
    async def same_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method in {"POST", "PUT", "DELETE", "PATCH"} and origin:
            allowed = {
                str(request.base_url).rstrip("/"),
                "http://127.0.0.1:5176",
                "http://localhost:5176",
            }
            if origin not in allowed:
                return JSONResponse(
                    {"detail": "Cross-origin writes are not allowed"}, status_code=403
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def require(identifier):
        row = db.get(identifier)
        if row is None:
            raise HTTPException(404, "Message not found")
        return row

    async def screen(identifier, mode):
        row = require(identifier)
        message = row["message"]
        request = prepare(message)
        fp = fingerprint(message)
        db.update(identifier, status="screening", error=None, event="screening")
        start = time.perf_counter()
        try:
            if mode == "recorded":
                saved = replay.get(fp)
                if saved is None or saved["request"] != request:
                    raise ValueError(
                        "No recording exists for this text. Edited messages require live inference."
                    )
                if saved.get("error"):
                    raise ValueError("The saved model call failed")
                raw = saved["raw_response"]
                model_ms = saved["model_ms"]
                metadata = recording["metadata"]
            else:
                async with httpx.AsyncClient(timeout=90, follow_redirects=False) as client:
                    response = await client.post(endpoint + "/predict", json=request)
                    if response.status_code == 400:
                        raise ValueError(response.json().get("detail", "Model input rejected"))
                    response.raise_for_status()
                    data = response.json()
                raw, model_ms, metadata = data["result"], data["model_ms"], data["metadata"]
            prediction = decode(raw)
            return db.update(
                identifier,
                status="screened",
                prediction=prediction,
                mode=mode,
                model_ms=model_ms,
                wall_ms=round((time.perf_counter() - start) * 1000, 3),
                model=metadata,
                raw_response=raw,
                request=request,
                fingerprint=fp,
                rules=rules(message),
                tfidf=predict_linear(message["body"], linear),
                screened_at=now(),
                event="screened",
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            detail = (
                str(exc)
                if isinstance(exc, ValueError)
                else "Model service failed. No prediction was substituted."
            )
            return db.update(identifier, status="error", error=detail, event="screening_failed")

    app.state.screen = screen

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "live_enabled": enabled}

    @app.get("/api/state")
    async def state():
        return {
            "messages": db.all(),
            "job": job,
            "config": {"live_enabled": enabled, "recorded_model": recording["metadata"]},
        }

    @app.get("/api/evaluation")
    async def evaluation():
        def compact(report):
            return {
                "summary": report["summary"],
                "metadata": report["metadata"],
                "created_at": report["created_at"],
                "cases": [
                    {
                        "id": r["case_id"],
                        "dataset": r["dataset"],
                        "expected": r["expected"],
                        "prediction": r.get("prediction"),
                        "error": r.get("error"),
                        "model_ms": r.get("model_ms"),
                        "message": r["request"]["state"],
                        "rules": r["rules"],
                        "tfidf_spam": r["tfidf_spam"],
                    }
                    for r in report["rows"]
                ],
            }

        training = json.loads((ROOT / "models/training-manifest.json").read_text())
        history = json.loads((ROOT / "models/training-history.json").read_text())
        bedrock_path = ROOT / "evals/bedrock.json"
        return {
            "base": compact(base),
            "specialist": compact(recording),
            "training": training,
            "history": history,
            "bedrock": json.loads(bedrock_path.read_text()) if bedrock_path.exists() else None,
            "data": json.loads((ROOT / "evals/data-manifest.json").read_text()),
        }

    async def run_batch(identifiers, mode):
        try:
            for identifier in identifiers:
                async with lock:
                    await app.state.screen(identifier, mode)
                job["completed"] += 1
                if mode == "recorded":
                    await asyncio.sleep(
                        0.35
                    )  # Visible playback pacing, never presented as model latency.
        finally:
            job["running"] = False

    @app.post("/api/run", status_code=202)
    async def run(body: Run):
        if body.mode == "live" and not enabled:
            raise HTTPException(403, "Live inference is disabled on this server")
        if job["running"] or lock.locked():
            raise HTTPException(409, "A screening run is already active")
        pending = [r for r in db.all() if r["status"] in {"pending", "error"}]
        if body.mode == "recorded" and any(
            fingerprint(r["message"]) not in replay for r in pending
        ):
            raise HTTPException(409, "Some messages have edited text and require live inference")
        job.update(running=True, completed=0, total=len(pending), mode=body.mode)
        task = asyncio.create_task(run_batch([r["id"] for r in pending], body.mode))
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return job

    @app.post("/api/variants")
    async def variant(body: Variant):
        if not enabled:
            raise HTTPException(403, "Edited text needs a running live model")
        if job["running"] or lock.locked():
            raise HTTPException(409, "Wait for the active screening run")
        if len(db.all()) >= 200:
            raise HTTPException(409, "This local demo is limited to 200 messages")
        if body.parent_id:
            require(body.parent_id)
        async with lock:
            identifier = "V-" + uuid.uuid4().hex[:12]
            db.insert(identifier, body.message.model_dump(), body.parent_id)
            return await app.state.screen(identifier, "live")

    @app.post("/api/messages/{identifier}/review")
    async def review(identifier: str, body: Review):
        row = require(identifier)
        if row["status"] != "screened":
            raise HTTPException(409, "Screen the message before reviewing it")
        return db.update(
            identifier,
            review={"label": body.label, "note": body.note, "at": now()},
            event="reviewed",
        )

    @app.get("/api/export/reviews")
    async def export_reviews():
        def family(row):
            while row["parent_id"]:
                row = require(row["parent_id"])
            return row["id"]

        examples = [
            {
                "id": r["id"],
                "group": family(r),
                "message": r["message"],
                "label": r["review"]["label"],
                "review": r["review"],
                "source_fingerprint": r["fingerprint"],
            }
            for r in db.all()
            if r.get("review")
        ]
        return JSONResponse(
            {"format": "frontdoor.reviewed.v1", "examples": examples},
            headers={"Content-Disposition": 'attachment; filename="frontdoor-reviewed.json"'},
        )

    @app.get("/api/evaluation/{variant}/export")
    async def export_evaluation(variant: Literal["base", "specialist"]):
        return JSONResponse(
            base if variant == "base" else recording,
            headers={"Content-Disposition": f'attachment; filename="frontdoor-{variant}.json"'},
        )

    @app.get("/api/messages/{identifier}/export")
    async def export_message(identifier: str):
        return JSONResponse(
            require(identifier),
            headers={"Content-Disposition": 'attachment; filename="frontdoor-decision.json"'},
        )

    dist = ROOT / "dist"
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/")
    async def index():
        if (dist / "index.html").exists():
            return FileResponse(dist / "index.html")
        return JSONResponse({"message": "Build the frontend, then restart this server."})

    return app
