# FrontDoor specialist

**Status: research checkpoint. Not a validated phishing filter.**

Base: [`convaiinnovations/laya`](https://huggingface.co/convaiinnovations/laya/tree/55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851), immutable revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`.

Derivative weights: Apache License 2.0. Original Laya work by Convai Innovations; FrontDoor modifications by Debojit Roy, 2026. No endorsement or affiliation is implied.

The release asset contains the **replacement parameters** for the decision head and final two encoder layers, stored as safetensors. It is a partial checkpoint, not a LoRA adapter and not a standalone model. Apply it to the pinned base using `frontdoor.worker`. All other parameters remain those of the original checkpoint. The worker validates the manifest, base revision, parameter names, and SHA-256 before loading.

SHA-256: `c886e8438e86ee6e0d8d4169f852d32687ac03a2746285884dea95de7905be5c`

Training: supervised cross-entropy on 670 messages / 840 binary questions; validation 117 messages / 134 questions. Final two encoder layers and decision head are trainable, totaling 50,762,753 parameters. Twelve epochs; AdamW; seed 42; batch 8; encoder LR 5e-5; head LR 2e-4; weight decay .01; gradient clipping 1; fp16 autocast with gradient scaling. Epoch 9 selected by minimum validation cross-entropy. Three early optimizer steps skipped by dynamic gradient scaling; none skipped after epoch 1.

Training time: 246.52 seconds on one Tesla T4, excluding loading and tokenization. Full history and parameter manifest are alongside this card. The initial unsuccessful four-epoch experiment remains in `evals/history/`.

Inputs: a JSON state containing subject, body and recipient context, plus the versioned binary questions in `server/frontdoor/engine.py`. Maximum total sequence length 512, question head 256. Long inputs are rejected in the worker. No sender authentication, URL lookup, or attachment interpretation occurs.

Outputs: two typed choices with probability scores. No calibration was fitted; inherited temperature scaling was reset to 1. These probabilities are **uncalibrated on FrontDoor's task**.

Evaluation: 95% accuracy on 200 sampled SMS messages; 90.24% on 41 public phishing messages; 56.67% on 30 authored development cases; 41.67% on 12 showcase cases. The conventional SMS baseline scored 94.5%. Broader phishing quality gates fail.

The second training schedule was chosen after seeing first-run evaluation results. No test examples enter training or validation-based checkpoint selection, but published numbers are exploratory and require new external validation. See [`evals/DATA.md`](../evals/DATA.md).

Intended use: local research, reproducible experimentation, and portfolio demonstrations of full-stack ML evaluation. It is not intended for autonomous security enforcement or production mail delivery.
