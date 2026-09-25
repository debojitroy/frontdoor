"""Supervised specialization of Laya's head and last two encoder layers on one GPU.

Public train/validation groups and original teaching examples only. Neither the showcase,
authored challenge nor either public test partition enters optimization or selection.
"""

import argparse
import json
import random
import time
from datetime import UTC, datetime
from pathlib import Path

from frontdoor.engine import QUESTIONS, digest, text_digest

ROOT = Path(__file__).resolve().parents[1]


def teaching_examples():
    examples = []
    offers = [
        "We sell bundles of website traffic. Reply to receive our price list.",
        "Our agency offers bulk social-media followers. Ask about our reseller package.",
        "Join our paid referral program to earn commission from new recruits.",
        "We have discounted wholesale accessories available. Contact our sales team.",
        "Buy a placement in our advertising directory. This is a commercial promotion.",
        "Our online course teaches ways to increase your business revenue. Enroll today.",
    ]
    for i, body in enumerate(offers):
        for context, spam in [
            ("An unsolicited mass advertisement from an unknown sender.", True),
            ("You requested this product information from the seller.", False),
        ]:
            examples.append(
                (
                    f"offer-{i}",
                    {"subject": "Product information", "body": body, "context": context},
                    {"spam": spam, "phishing": False},
                )
            )
    pairs = [
        (
            "Send the current digits from your authenticator to our agent.",
            "Never send the digits from your authenticator to anyone.",
        ),
        (
            "Give our support team your recovery phrase to repair the wallet.",
            "Keep your recovery phrase private. Our support team will never ask for it.",
        ),
        (
            "Send your account password in a reply so we can inspect your files.",
            "Change your password in the app. Do not send it in a reply.",
        ),
        (
            "Purchase prepaid vouchers and send the redemption numbers to me. Bypass approval.",
            "Please report anyone asking you to purchase vouchers and send redemption numbers.",
        ),
        (
            "Pay this invoice to a new account and do not contact the supplier to verify.",
            "Before paying changed bank details, contact the supplier through a known number.",
        ),
        (
            "Enter your bank card details on our unrelated site to receive unexpected prize money.",
            "Be careful of sites asking for bank card details to receive unexpected prize money.",
        ),
        (
            "We need your private sign-in backup codes to prevent your profile being suspended.",
            "Save your sign-in backup codes privately. Never share them to prevent suspension.",
        ),
        (
            "Disable your account protection and approve the sign-in you did not initiate.",
            "Reject sign-ins you did not initiate and keep your account protection enabled.",
        ),
    ]
    for i, (attack, advice) in enumerate(pairs):
        examples.append(
            (
                f"teaching-{i}",
                {
                    "subject": "Account assistance",
                    "body": attack,
                    "context": "An unexpected message from a stranger.",
                },
                {"spam": True, "phishing": True},
            )
        )
        examples.append(
            (
                f"teaching-{i}",
                {
                    "subject": "Safety advice",
                    "body": advice,
                    "context": "Advice published by your own security team.",
                },
                {"spam": False, "phishing": False},
            )
        )
    return examples


def build_data():
    sms_train = json.loads((ROOT / "data/sms-train.json").read_text())
    sms_val = json.loads((ROOT / "data/sms-validation.json").read_text())
    source = [
        json.loads(line)
        for line in (ROOT / "data/phishing-source.jsonl").read_text().splitlines()
        if line
    ]
    phish = [
        {
            "id": r["id"],
            "group": text_digest(r["subject"] + " " + r["body"]),
            "message": {"subject": r["subject"], "body": r["body"], "context": ""},
            "expected": r["label"] == "phishing",
        }
        for r in source
    ]
    p_train = [r for r in phish if int(r["group"][:8], 16) % 10 < 7]
    p_val = [r for r in phish if int(r["group"][:8], 16) % 10 == 7]
    p_test = [r for r in phish if int(r["group"][:8], 16) % 10 >= 8]
    train, val = [], []
    for label in (False, True):
        selected = sorted(
            [r for r in sms_train if r["expected"] == label], key=lambda r: r["group"]
        )[:250]
        train.extend((r["group"], r["message"], {"spam": label}) for r in selected)
        selected_val = sorted(
            [r for r in sms_val if r["expected"] == label], key=lambda r: r["group"]
        )[:50]
        val.extend((r["group"], r["message"], {"spam": label}) for r in selected_val)
    for target, records in ((train, p_train), (val, p_val)):
        target.extend(
            (r["group"], r["message"], {"spam": r["expected"], "phishing": r["expected"]})
            for r in records
        )
    train.extend(teaching_examples())
    (ROOT / "evals/phishing-test.json").write_text(json.dumps(p_test, indent=2) + "\n")
    return (
        train,
        val,
        {
            "public_phishing": {
                "dataset": "darkknight25/phishing_benign_email_dataset",
                "revision": "8a0e4433b22b31690cc24443f17d2b2afec9dea9",
                "license": "MIT",
                "train": len(p_train),
                "validation": len(p_val),
                "test": len(p_test),
                "test_hash": digest(p_test),
                "limits": "Small curated public corpus, apparently templated; labels and provenance not independently audited.",
            },
            "train_hash": digest(train),
            "validation_hash": digest(val),
            "train_examples": len(train),
            "validation_examples": len(val),
            "teaching_examples": len(teaching_examples()),
            "selection": "Lowest validation cross-entropy; checkpoint selection never uses test labels.",
            "development_limit": "Teaching examples were written after observing base-model development failures. Original challenge results are development results.",
        },
    )


def main(args):
    import laya
    import torch
    from huggingface_hub import snapshot_download
    from laya.common import QTYPES, build_sequence
    from safetensors.torch import save_file

    random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(4)
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    train, validation, meta = build_data()
    meta.update(
        created_at=datetime.now(UTC).isoformat(),
        epochs=args.epochs,
        encoder_lr=args.encoder_lr,
        head_lr=args.head_lr,
        seed=42,
        base_revision="55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851",
    )
    (output / "training-manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    (output / "training-data.json").write_text(json.dumps(train, indent=2) + "\n")
    (output / "validation-data.json").write_text(json.dumps(validation, indent=2) + "\n")
    base = snapshot_download(
        "convaiinnovations/laya",
        revision=meta["base_revision"],
        allow_patterns=["rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*"],
    )
    agent = laya.load(base, device="cuda")
    model = agent.model
    layer_names = [
        name for name, _ in model.named_parameters() if name.startswith("encoder.layers.")
    ]
    last = max(int(name.split(".")[2]) for name in layer_names)
    for name, param in model.named_parameters():
        param.requires_grad = not name.startswith(("encoder.", "act_head.")) or any(
            name.startswith(f"encoder.layers.{i}.") for i in (last - 1, last)
        )
    params = [(name, p) for name, p in model.named_parameters() if p.requires_grad]
    meta["trainable_parameters"] = sum(p.numel() for _, p in params)
    meta["trainable_names"] = [name for name, _ in params]
    (output / "training-manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("Trainable parameters", meta["trainable_parameters"], flush=True)

    def encode(examples, shuffle_options=False):
        items = []
        for _, state, labels in examples:
            for task, positive in labels.items():
                q = QUESTIONS[task]
                keys = list(q["criteria"])
                if shuffle_options and random.random() < 0.5:
                    keys.reverse()
                crit = {key: q["criteria"][key] for key in keys}
                ids, markers = build_sequence(
                    agent.tok,
                    state,
                    {"t": "choice", "ins": q["instructions"], "crit": crit},
                    512,
                    256,
                )
                if len(markers) != 2:
                    raise ValueError("Unexpected option encoding")
                label = (
                    keys.index(task)
                    if positive
                    else next(i for i, k in enumerate(keys) if k != task)
                )
                items.append((ids, markers, label))
        return items

    def batch(items):
        length = max(len(x[0]) for x in items)
        ids = torch.full((len(items), length), agent.tok.pad_token_id, dtype=torch.long)
        att = torch.zeros_like(ids)
        for i, (tokens, _, _) in enumerate(items):
            ids[i, : len(tokens)] = torch.tensor(tokens)
            att[i, : len(tokens)] = 1
        return [
            ids.cuda(),
            att.cuda(),
            torch.tensor([x[1] for x in items], device="cuda"),
            torch.ones((len(items), 2), dtype=torch.bool, device="cuda"),
            torch.full((len(items),), QTYPES["choice"], device="cuda", dtype=torch.long),
            torch.tensor([x[2] for x in items], device="cuda"),
        ]

    optimizer = torch.optim.AdamW(
        [
            {"params": [p for n, p in params if n.startswith("encoder.")], "lr": args.encoder_lr},
            {"params": [p for n, p in params if not n.startswith("encoder.")], "lr": args.head_lr},
        ],
        weight_decay=0.01,
    )
    scaler = torch.amp.GradScaler("cuda")
    best = float("inf")
    history = []
    started = time.perf_counter()
    validation_items = encode(validation)
    for epoch in range(args.epochs):
        model.train()
        model.encoder.eval()  # Frozen layers use stable features; selected layers still get gradients.
        items = encode(train, True)
        random.shuffle(items)
        losses = []
        skipped_steps = 0
        for step, start in enumerate(range(0, len(items), 8)):
            b = batch(items[start : start + 8])
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16):
                logits, _ = model(*b[:5])
                loss = torch.nn.functional.cross_entropy(logits.float(), b[5])
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_([p for _, p in params], 1)
            previous_scale = scaler.get_scale()
            scaler.step(optimizer)
            scaler.update()
            skipped_steps += int(scaler.get_scale() < previous_scale)
            losses.append(loss.item())
            if step % 20 == 0:
                print(f"epoch {epoch + 1} step {step} loss {loss.item():.4f}", flush=True)
        model.eval()
        total = 0
        correct = 0
        count = 0
        with torch.no_grad():
            for start in range(0, len(validation_items), 8):
                b = batch(validation_items[start : start + 8])
                with torch.autocast("cuda", dtype=torch.float16):
                    logits, _ = model(*b[:5])
                total += torch.nn.functional.cross_entropy(
                    logits.float(), b[5], reduction="sum"
                ).item()
                correct += (logits.argmax(-1) == b[5]).sum().item()
                count += len(b[5])
        score = total / count
        history.append(
            {
                "epoch": epoch + 1,
                "train_loss": sum(losses) / len(losses),
                "validation_loss": score,
                "validation_accuracy": correct / count,
                "skipped_steps": skipped_steps,
                "elapsed_seconds": round(time.perf_counter() - started, 2),
            }
        )
        if score < best:
            best = score
            weights = {name: p.detach().half().contiguous().cpu() for name, p in params}
            save_file(weights, str(output / "adapter.safetensors"))
            meta["selected_epoch"] = epoch + 1
        (output / "history.json").write_text(json.dumps(history, indent=2) + "\n")
        print("VALIDATION", history[-1], flush=True)
    meta["adapter_sha256"] = (
        __import__("hashlib").sha256((output / "adapter.safetensors").read_bytes()).hexdigest()
    )
    meta["duration_seconds"] = round(time.perf_counter() - started, 2)
    meta["calibration"] = (
        "No calibration fitted. Reset inherited temperatures to 1; all scores remain uncalibrated."
    )
    (output / "training-manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(
        json.dumps({k: v for k, v in meta.items() if k != "trainable_names"}, indent=2), flush=True
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "data/specialist-v1")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--encoder-lr", type=float, default=5e-5)
    parser.add_argument("--head-lr", type=float, default=2e-4)
    main(parser.parse_args())
