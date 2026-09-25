# Data and evaluation protocol

## What the counts mean

| Collection | Training | Validation | Evaluation | Labels |
| --- | ---: | ---: | ---: | --- |
| UCI SMS | 3,984 for TF–IDF; 500 for specialization | 525 available; 100 for specialization | 200 | spam / not spam |
| Public phishing | 142 | 17 | 41 | phishing / benign |
| Original teaching examples | 28 | 0 | 0 | spam and phishing |
| Original development examples | 0 | 0 | 30 | legitimate / spam / phishing |
| Original showcase | 0 | 0 | 12 | legitimate / spam / phishing |

670 training and 117 validation **messages** expand to 840 training and 134 validation binary **questions**. The public phishing examples provide both spam and phishing targets; their spam target treats phishing attempts as unwanted/scam messages. SMS contributes only spam targets.

`data-manifest.json` records the public SMS archive checksum, split hashes, and original authored hashes. `models/phishing-source.json` pins the phishing source revision and file hash. `models/training-manifest.json` records the training and validation hashes, base revision, selected epoch, updated parameter names, and adapter checksum.

## Splitting

We lowercase text, replace URL tokens and digit sequences, normalize punctuation and whitespace, and hash the result. Hash buckets 0–6 train, 7 validate, 8–9 test. The SMS evaluation takes the first 100 legitimate and 100 spam examples sorted by normalized group hash and original ID. Its class balance is deliberate; precision and accuracy will differ at real inbox prevalence.

Normalized duplicate groups never cross partitions. This does not guarantee independent campaigns: similar templates can still appear in different groups. The public phishing corpus is small and apparently templated, making this limitation substantial.

Labels, intent, technique, target, and spoofed-sender fields from the phishing source never enter model input. Inference sees only subject, body, and an empty context. Authored examples include explicit recipient context as a task input, not independently observed identity evidence.

## Experiment chronology

1. Freeze the original 12 showcase and 30 challenge examples and the SMS split. Run English base Laya. Investigate the multilingual checkpoint on the showcase only; retain those records in `history/`.
2. After observing the base failures, write 28 teaching examples distinguishing unsolicited ads, requested information, deceptive requests, and security advice.
3. Pin and partition the public phishing corpus. Train the first specialist for four epochs. Select epoch 1 by validation cross-entropy. Evaluate all 283 messages.
4. Inspect the first specialist results. Change **only the training schedule/rates**, using the same training and validation messages, binary prompts, and frozen quality thresholds. Train for 12 epochs; select epoch 9 by validation loss.
5. Evaluate the second checkpoint on all 283 messages. No further tuning. Preserve the failed first experiment and publish both improved and regressed metrics.
6. Run an offline Bedrock Sonnet 4.6 comparator over all 42 authored messages with no labels included in its input.

**Test results were observed between training experiments.** The public partitions are held out from optimization and checkpoint selection but are not an untouched final holdout for the second experiment. These are exploratory comparisons, not a blinded external validation. The authored challenge is development data. An independently collected final evaluation is still needed.

## Scope and uncertainty

The SMS corpus is old public data; overlap with upstream Laya training is unknown. The phishing corpus's labels and source provenance have not been independently audited. Authored labels are the developer's judgments, not multi-annotator consensus. Dataset size is too small to establish superiority over TF–IDF or robustness to new campaigns, languages, attachments, or prompt injection.

No confidence calibration was fitted on this task. The UI's review route is an application heuristic, not evidence that mistakes are always detected. Zero observed dangerous inbox suggestions in a small authored set is not a guarantee of safe routing.

The frozen `protocol.json` retains its original challenge description for evidence reproducibility. This document supplies the later experimental history and limits. Its thresholds were not changed after observing failures.

## Provenance

**SMS Spam Collection** — Almeida, T. and Hidalgo, J. (2012), UCI Machine Learning Repository. DOI: https://doi.org/10.24432/C5CC84. [Dataset page](https://archive.ics.uci.edu/dataset/228/sms+spam+collection). Licensed CC BY 4.0. We selected a subset, assigned split/group metadata, and wrapped original messages in JSON; text was preserved.

**Phishing and Benign Email Dataset** — `darkknight25`, dataset card identifies “sunny thakur.” [Pinned card](https://huggingface.co/datasets/darkknight25/phishing_benign_email_dataset/blob/8a0e4433b22b31690cc24443f17d2b2afec9dea9/README.md). Card declares MIT. We retain subject, body and labels, add split metadata, and exclude label-revealing auxiliary fields. Public text can contain domains or phone numbers; the app renders it as inert text and never visits those destinations.

**Original examples** — authored for FrontDoor in `scripts/prepare_data.py` and `scripts/train_specialist.py`, licensed under the repository MIT license. Showcase and development examples have distinct wording. There is no claim they are independent campaign samples.
