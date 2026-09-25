"""Optional pinned Laya service. No generative API or network access to message links."""

import json
import os
import re
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

MODEL_REPO = "convaiinnovations/laya"
MODEL_REVISION = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: dict
    questions: dict


@asynccontextmanager
async def lifespan(app):
    import laya
    import torch
    import transformers
    from huggingface_hub import snapshot_download

    repo = os.getenv("FRONTDOOR_MODEL_REPO", MODEL_REPO)
    revision = os.getenv("FRONTDOOR_MODEL_REVISION", MODEL_REVISION)
    if ("FRONTDOOR_MODEL_REPO" in os.environ) != ("FRONTDOOR_MODEL_REVISION" in os.environ):
        raise ValueError("Set both FRONTDOOR_MODEL_REPO and FRONTDOOR_MODEL_REVISION")
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("An immutable model revision is required")
    path = snapshot_download(
        repo,
        revision=revision,
        allow_patterns=["rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*"],
    )
    device = os.getenv("FRONTDOOR_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
    app.state.agent = laya.load(path, device=device)
    adapter_info = None
    adapter_dir = os.getenv("FRONTDOOR_ADAPTER_DIR")
    if adapter_dir:
        import hashlib
        from pathlib import Path

        from safetensors.torch import load_file

        folder = Path(adapter_dir)
        adapter_info = json.loads((folder / "training-manifest.json").read_text())
        weights_path = folder / "adapter.safetensors"
        checksum = hashlib.sha256(weights_path.read_bytes()).hexdigest()
        if adapter_info["base_revision"] != revision or checksum != adapter_info["adapter_sha256"]:
            raise ValueError("Specialist adapter does not match its manifest or base model")
        weights = load_file(str(weights_path))
        expected = set(adapter_info["trainable_names"])
        if set(weights) != expected or not expected.issubset(app.state.agent.model.state_dict()):
            raise ValueError("Unexpected specialist adapter parameters")
        app.state.agent.model.load_state_dict(weights, strict=False)
        app.state.agent.temperature = [1.0, 1.0, 1.0]
        app.state.agent.temperature_by_options = {}
        app.state.agent.lang_temperatures = {}
    app.state.lock = threading.Lock()
    app.state.metadata = {
        "model_repo": repo,
        "model_revision": revision,
        "laya_version": laya.__version__,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "device": device,
        "hardware": torch.cuda.get_device_name(0) if device == "cuda" else "CPU",
        "max_len": min(1024, app.state.agent.cfg.get("max_len", 512)),
        "head_max_len": 256,
        "variant": "specialist" if adapter_info else "base",
        "adapter_sha256": adapter_info["adapter_sha256"] if adapter_info else None,
    }
    yield


app = FastAPI(title="FrontDoor Laya worker", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ready", **app.state.metadata}


@app.post("/predict")
def predict(body: Request):
    import torch
    from laya.common import render_options, serialize_state

    if len(json.dumps(body.model_dump())) > 14000 or not 1 <= len(body.questions) <= 2:
        raise HTTPException(400, "Supply one or two bounded binary questions")
    agent = app.state.agent
    state_tokens = len(agent.tok.encode(serialize_state(body.state), add_special_tokens=False))
    for name, q in body.questions.items():
        if (
            name not in {"spam", "phishing"}
            or not isinstance(q, dict)
            or q.get("type") != "choice"
            or not isinstance(q.get("criteria"), dict)
            or len(q["criteria"]) != 2
            or not isinstance(q.get("instructions"), str)
            or any(not isinstance(v, str) for v in q["criteria"].values())
        ):
            raise HTTPException(400, "Invalid binary question")
        options = render_options({"t": "choice", "crit": q["criteria"]})
        lengths = [
            len(agent.tok.encode(" " + option, add_special_tokens=False)) for option in options
        ]
        head_tokens = (
            len(agent.tok.encode("choice question: " + q["instructions"], add_special_tokens=False))
            + sum(lengths)
            + 2
        )
        if (
            max(lengths) > 48
            or head_tokens > 256
            or state_tokens + head_tokens + 4 > app.state.metadata["max_len"]
        ):
            raise HTTPException(400, "Message exceeds model token budget; shorten it")
    with app.state.lock:
        started = time.perf_counter()
        raw = agent.predict(
            body.state,
            body.questions,
            max_len=app.state.metadata["max_len"],
            head_max_len=256,
        )
        if agent.device.type == "cuda":
            torch.cuda.synchronize()
        elapsed = round((time.perf_counter() - started) * 1000, 3)
    metadata = {
        **app.state.metadata,
        "device": str(agent.device),
        "hardware": torch.cuda.get_device_name(agent.device)
        if agent.device.type == "cuda"
        else "CPU",
    }
    return {"result": raw, "model_ms": elapsed, "metadata": metadata}
