import copy
import hashlib
import json
from pathlib import Path

import pytest
from frontdoor.engine import decode, digest, fingerprint, prepare, text_digest
from frontdoor.evaluation import binary, verify
from frontdoor.linear import predict_linear

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads((ROOT / path).read_text())


@pytest.fixture
def inputs():
    datasets = {
        "sms": load("evals/sms-test.json"),
        "phishing": load("evals/phishing-test.json"),
        "challenge": load("evals/challenge.json"),
        "showcase": load("fixtures/messages.json"),
    }
    return datasets, load("evals/protocol.json"), load("models/spam-linear.json")


@pytest.mark.parametrize(
    "file", ["evals/base.json", "evals/specialist.json", "evals/history/specialist-v1.json"]
)
def test_all_recorded_results_recompute(file, inputs):
    verify(load(file), *inputs)


@pytest.mark.parametrize(
    "change",
    [
        "truth",
        "input",
        "fingerprint",
        "probability",
        "prediction",
        "summary",
        "drop",
        "duplicate",
        "tfidf",
        "timing",
    ],
)
def test_evidence_tampering_is_detected(change, inputs):
    report = load("evals/specialist.json")
    row = report["rows"][0]
    if change == "truth":
        row["expected"] = not row["expected"]
    elif change == "input":
        row["request"]["state"]["body"] += " altered"
    elif change == "fingerprint":
        row["fingerprint"] = "wrong"
    elif change == "probability":
        row["raw_response"]["answers"]["spam"]["probabilities"]["spam"] = float("nan")
    elif change == "prediction":
        row["prediction"]["spam"]["choice"] = "wrong"
    elif change == "summary":
        report["summary"]["sms"]["laya"]["accuracy"] = 1
    elif change == "drop":
        report["rows"].pop()
    elif change == "duplicate":
        report["rows"][1] = copy.deepcopy(row)
    elif change == "tfidf":
        row["tfidf_spam"] = not row["tfidf_spam"]
    else:
        row["model_ms"] = -1
    with pytest.raises(ValueError):
        verify(report, *inputs)


def test_missing_predictions_stay_in_denominator():
    result = binary([True, False, True, False], [True, None, None, False])
    assert result["accuracy"] == 0.5
    assert result["recall"] == 0.5
    assert result["errors"] == 2


def test_labels_and_sender_do_not_enter_model_input():
    message = load("fixtures/messages.json")[0]["message"]
    original = fingerprint(message)
    changed = {**message, "sender": "phishing", "expected": "spam", "label": "phishing"}
    assert prepare(changed) == prepare(message)
    assert fingerprint(changed) == original
    changed["context"] += " different context"
    assert fingerprint(changed) != original


def test_no_three_class_verdict_from_single_binary_answer():
    raw = load("evals/specialist.json")["rows"][0]["raw_response"]
    assert "verdict" not in decode(raw, ("spam",))


def test_normalized_duplicate_grouping():
    assert text_digest("Visit https://one.example 123 NOW!") == text_digest(
        "visit https://two.example 456 now"
    )


def test_selected_checkpoint_matches_validation_and_recording():
    meta = load("models/training-manifest.json")
    history = load("models/training-history.json")
    assert meta["selected_epoch"] == min(history, key=lambda h: h["validation_loss"])["epoch"]
    assert load("evals/specialist.json")["metadata"]["adapter_sha256"] == meta["adapter_sha256"]
    assert load("evals/specialist.json")["metadata"]["model_revision"] == meta["base_revision"]


def test_optional_bedrock_evidence_has_same_inputs():
    report = load("evals/bedrock.json")
    datasets = {
        "challenge": load("evals/challenge.json"),
        "showcase": load("fixtures/messages.json"),
    }
    assert report["dataset_hash"] == digest(datasets)
    cases = {(name, c["id"]): c for name, rows in datasets.items() for c in rows}
    assert len(report["rows"]) == len(cases)
    assert len({(r["dataset"], r["case_id"]) for r in report["rows"]}) == len(cases)
    for row in report["rows"]:
        case = cases[(row["dataset"], row["case_id"])]
        assert row["state"] == prepare(case["message"])["state"]
        assert row["expected"] == case["expected"]
        if not row.get("error"):
            tool = row["response"]["content"][0]["toolUse"]
            assert tool["input"]["label"] == row["prediction"]
    for name in datasets:
        rows = [r for r in report["rows"] if r["dataset"] == name]
        assert report["summary"][name] == {
            "count": len(rows),
            "correct": sum(r.get("prediction") == r["expected"] for r in rows),
            "errors": sum(bool(r.get("error")) for r in rows),
        }


def test_linear_empty_text_and_fixture_consistency(inputs):
    model = inputs[2]
    assert 0 <= predict_linear("", model)["probability"] <= 1
    for row in load("evals/specialist.json")["rows"]:
        assert predict_linear(row["request"]["state"]["body"], model)["spam"] == row["tfidf_spam"]


def test_training_groups_exclude_public_test_and_authored_bodies():
    audit = load("models/split-audit.json")
    public_groups = {
        r["group"]
        for path in ("evals/sms-test.json", "evals/phishing-test.json")
        for r in load(path)
    }
    for training, validation in (
        ("baseline_train", "baseline_validation"),
        ("specialist_train", "specialist_validation"),
    ):
        assert not set(audit[training]["groups"]) & set(audit[validation]["groups"])
        assert not public_groups & set(audit[training]["groups"])
        assert not public_groups & set(audit[validation]["groups"])
    authored_bodies = {
        hashlib.sha256(r["message"]["body"].encode()).hexdigest()
        for path in ("evals/challenge.json", "fixtures/messages.json")
        for r in load(path)
    }
    assert not authored_bodies & set(audit["specialist_train"]["body_hashes"])
    manifest = load("models/training-manifest.json")
    assert audit["specialist_train"]["count"] == manifest["train_examples"]
    assert audit["specialist_validation"]["count"] == manifest["validation_examples"]


@pytest.mark.parametrize("raw", [None, [], {"answers": []}, {"answers": {"spam": None}}])
def test_malformed_model_payloads_are_rejected(raw):
    with pytest.raises(TypeError):
        decode(raw, ("spam",))
