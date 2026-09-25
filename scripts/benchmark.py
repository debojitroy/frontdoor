"""Record real local inference and a conventional, training-split-only spam baseline."""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from frontdoor.engine import decode, digest, fingerprint, prepare, rules
from frontdoor.evaluation import summarize, verify

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    paths = {
        "sms": "evals/sms-test.json",
        "challenge": "evals/challenge.json",
        "showcase": "fixtures/messages.json",
        "phishing": "evals/phishing-test.json",
    }
    datasets = {name: json.loads((ROOT / path).read_text()) for name, path in paths.items()}
    protocol = json.loads((ROOT / "evals/protocol.json").read_text())
    return datasets, protocol


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(path)


def run(args, datasets, protocol):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    if args.output.exists():
        raise ValueError("Choose a new output path; existing evidence is preserved")
    train = json.loads((ROOT / "data/sms-train.json").read_text())
    assert not {r["group"] for r in train} & {r["group"] for r in datasets["sms"]}
    classifier = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), max_features=20000, sublinear_tf=True),
        LogisticRegression(C=4, class_weight="balanced", random_state=42, max_iter=500),
    )
    started = time.perf_counter()
    classifier.fit([r["message"]["body"] for r in train], [r["expected"] for r in train])
    training_ms = round((time.perf_counter() - started) * 1000, 3)
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "protocol": protocol,
        "dataset_hash": digest(datasets),
        "tfidf": {
            "train_hash": digest(train),
            "training_ms": training_ms,
            "configuration": "word 1–2 grams, max_features=20000, sublinear_tf; balanced logistic regression C=4, seed=42, max_iter=500",
        },
        "rows": [],
    }
    save(args.output.with_suffix(".manifest.json"), report)
    with httpx.Client(base_url=args.url, timeout=120, follow_redirects=False) as client:
        health = client.get("/health")
        health.raise_for_status()
        report["metadata"] = health.json()
        for name, cases in datasets.items():
            tasks = (
                ("spam",)
                if name == "sms"
                else ("phishing",)
                if name == "phishing"
                else ("spam", "phishing")
            )
            for case in cases:
                request = prepare(case["message"], tasks)
                row = {
                    "dataset": name,
                    "case_id": case["id"],
                    "expected": case["expected"],
                    "fingerprint": fingerprint(case["message"], tasks),
                    "request": request,
                    "rules": rules(case["message"]),
                }
                start = time.perf_counter()
                row["tfidf_spam"] = bool(classifier.predict([case["message"]["body"]])[0])
                row["tfidf_ms"] = round((time.perf_counter() - start) * 1000, 3)
                start = time.perf_counter()
                try:
                    response = client.post("/predict", json=request)
                    response.raise_for_status()
                    data = response.json()
                    row.update(raw_response=data["result"], model_ms=data["model_ms"])
                    row["prediction"] = decode(data["result"], tasks)
                except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                    row.update(error=type(exc).__name__, model_ms=None)
                row["wall_ms"] = round((time.perf_counter() - start) * 1000, 3)
                report["rows"].append(row)
                save(args.output, report)
                if len(report["rows"]) % 20 == 0 or name != "sms":
                    print(
                        name,
                        case["id"],
                        row.get("prediction", {}).get("verdict", row.get("prediction", {})),
                        row.get("error"),
                        flush=True,
                    )
    report["summary"] = summarize(report["rows"], protocol)
    save(args.output, report)
    verify(report, datasets, protocol)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8141")
    parser.add_argument("--output", type=Path, default=ROOT / "data/candidate.json")
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--quality", action="store_true")
    args = parser.parse_args()
    datasets, protocol = inputs()
    if args.verify:
        report = json.loads(args.verify.read_text())
        linear = json.loads((ROOT / "models/spam-linear.json").read_text())
        verify(report, datasets, protocol, linear)
    else:
        report = run(args, datasets, protocol)
    print(json.dumps(report["summary"], indent=2))
    if args.quality and not all(report["summary"]["gates"].values()):
        raise SystemExit(1)
