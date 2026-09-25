import math
import statistics

from frontdoor.engine import decode, digest, fingerprint, prepare, rules


def binary(truth, predictions):
    tp = sum(y and p is True for y, p in zip(truth, predictions, strict=True))
    fp = sum(not y and p is True for y, p in zip(truth, predictions, strict=True))
    fn = sum(y and p is not True for y, p in zip(truth, predictions, strict=True))
    tn = sum(not y and p is False for y, p in zip(truth, predictions, strict=True))
    positives = sum(truth)
    negatives = len(truth) - positives
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / positives if positives else 0
    return {
        "count": len(truth),
        "correct": tp + tn,
        "accuracy": (tp + tn) / len(truth),
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
        "false_positive_rate": fp / negatives if negatives else 0,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "errors": sum(p is None for p in predictions),
    }


def summarize(rows, protocol):
    result = {}
    for dataset in ("sms", "challenge", "showcase", "phishing"):
        selected = [r for r in rows if r["dataset"] == dataset]
        if not selected:
            continue
        if dataset in {"sms", "phishing"}:
            task = "spam" if dataset == "sms" else "phishing"
            truth = [r["expected"] for r in selected]
            predictions = [
                None if r.get("error") else r["prediction"][task]["choice"] == task
                for r in selected
            ]
            result[dataset] = {
                "laya": binary(truth, predictions),
                "rules": binary(
                    truth,
                    [
                        r["rules"]["verdict"] != "legitimate"
                        if dataset == "sms"
                        else r["rules"]["verdict"] == "phishing"
                        for r in selected
                    ],
                ),
            }
            if dataset == "sms":
                result[dataset]["tfidf"] = binary(truth, [r["tfidf_spam"] for r in selected])
        else:
            correct = lambda r: not r.get("error") and r["prediction"]["verdict"] == r["expected"]
            phish = [r for r in selected if r["expected"] == "phishing"]
            legitimate = [r for r in selected if r["expected"] == "legitimate"]
            dangerous_inbox = [
                r
                for r in selected
                if not r.get("error")
                and r["prediction"]["route"] == "inbox"
                and r["expected"] != "legitimate"
            ]
            result[dataset] = {
                "count": len(selected),
                "correct": sum(bool(correct(r)) for r in selected),
                "accuracy": sum(bool(correct(r)) for r in selected) / len(selected),
                "rules_accuracy": sum(r["rules"]["verdict"] == r["expected"] for r in selected)
                / len(selected),
                "phishing_recall": sum(bool(correct(r)) for r in phish) / len(phish),
                "legitimate_false_flags": sum(
                    not r.get("error") and r["prediction"]["verdict"] != "legitimate"
                    for r in legitimate
                ),
                "unsafe_inbox_suggestions": len(dangerous_inbox),
                "errors": sum(bool(r.get("error")) for r in selected),
            }
        times = sorted(r["model_ms"] for r in selected if not r.get("error"))
        result[dataset]["p50_model_ms"] = statistics.median(times) if times else None
        result[dataset]["p95_model_ms"] = (
            times[min(len(times) - 1, int(len(times) * 0.95))] if times else None
        )
    t = protocol["thresholds"]
    result["gates"] = {
        "sms_spam_f1": result["sms"]["laya"]["f1"] >= t["minimum_sms_spam_f1"],
        "sms_false_positive_rate": result["sms"]["laya"]["false_positive_rate"]
        <= t["maximum_sms_false_positive_rate"],
        "challenge_accuracy": result["challenge"]["accuracy"] >= t["minimum_challenge_accuracy"],
        "challenge_phishing_recall": result["challenge"]["phishing_recall"]
        >= t["minimum_challenge_phishing_recall"],
        "no_execution_errors": all(not r.get("error") for r in rows),
    }
    return result


def verify(report, datasets, protocol, linear=None):
    if report["protocol"] != protocol or report["dataset_hash"] != digest(datasets):
        raise ValueError("Protocol or labeled data changed")
    cases = {(name, c["id"]): c for name, data in datasets.items() for c in data}
    if len(report["rows"]) != len(cases):
        raise ValueError("Missing or extra results")
    seen = set()
    for row in report["rows"]:
        key = row["dataset"], row["case_id"]
        if key in seen or key not in cases:
            raise ValueError("Duplicate or unknown result")
        seen.add(key)
        case = cases[key]
        tasks = (
            ("spam",)
            if row["dataset"] == "sms"
            else ("phishing",)
            if row["dataset"] == "phishing"
            else ("spam", "phishing")
        )
        if (
            row["expected"] != case["expected"]
            or row["request"] != prepare(case["message"], tasks)
            or row["fingerprint"] != fingerprint(case["message"], tasks)
            or row["rules"] != rules(case["message"])
        ):
            raise ValueError("Input, annotation, fingerprint or baseline changed")
        if not row.get("error") and row["prediction"] != decode(row["raw_response"], tasks):
            raise ValueError("Prediction differs from recorded response")
        if not row.get("error") and (
            not isinstance(row["model_ms"], (int, float))
            or not math.isfinite(row["model_ms"])
            or row["model_ms"] < 0
        ):
            raise ValueError("Invalid model timing")
        if linear is not None:
            from frontdoor.linear import predict_linear

            if (
                report["tfidf"]["train_hash"] != linear["train_hash"]
                or row["tfidf_spam"] != predict_linear(case["message"]["body"], linear)["spam"]
            ):
                raise ValueError("Stored TF-IDF baseline differs from the bundled model")
    actual = summarize(report["rows"], protocol)
    if actual != report["summary"]:
        raise ValueError("Summary does not match recorded results")
    return actual
