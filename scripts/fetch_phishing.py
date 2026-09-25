"""Download the pinned public corpus, verifying bytes before making them available."""

import hashlib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION = "8a0e4433b22b31690cc24443f17d2b2afec9dea9"
URL = (
    "https://huggingface.co/datasets/darkknight25/phishing_benign_email_dataset/resolve/"
    + REVISION
    + "/phishing%20and%20benign%20email%20dataset.jsonl"
)


def main():
    manifest = __import__("json").loads((ROOT / "models/phishing-source.json").read_text())
    raw = urllib.request.urlopen(URL, timeout=60).read()
    if hashlib.sha256(raw).hexdigest() != manifest["sha256"]:
        raise ValueError("Public phishing source bytes changed")
    output = ROOT / "data/phishing-source.jsonl"
    output.parent.mkdir(exist_ok=True)
    output.write_bytes(raw)
    print("Downloaded and verified the pinned public phishing corpus")


if __name__ == "__main__":
    main()
