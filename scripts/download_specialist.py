"""Fetch the published adapter and verify it before use. Does not download the base model."""

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://github.com/debojitroy/frontdoor/releases/download/v0.1.0/frontdoor-specialist.safetensors"


def main(destination):
    manifest = ROOT / "models/training-manifest.json"
    expected = json.loads(manifest.read_text())["adapter_sha256"]
    destination.mkdir(parents=True, exist_ok=True)
    final = destination / "adapter.safetensors"
    if final.exists():
        with final.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError("Destination contains different weights; choose an empty directory")
        print("Existing specialist weights verified")
        shutil.copyfile(manifest, destination / "training-manifest.json")
        return
    with tempfile.TemporaryDirectory(dir=destination) as temporary:
        path = Path(temporary) / "download"
        with urllib.request.urlopen(URL, timeout=90) as response, path.open("wb") as stream:
            shutil.copyfileobj(response, stream)
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError("Downloaded weights do not match the published SHA-256")
        path.replace(final)
    shutil.copyfile(manifest, destination / "training-manifest.json")
    print(f"Verified specialist saved in {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "data/specialist")
    main(parser.parse_args().output)
