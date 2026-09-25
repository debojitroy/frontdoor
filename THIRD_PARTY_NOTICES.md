# Third-party notices

## Laya

Base model and library by **Convai Innovations**. Base model: https://huggingface.co/convaiinnovations/laya at revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`. Model card declares Apache License 2.0. The derivative FrontDoor specialist weights are distributed under Apache License 2.0; application code is MIT.

The release contains changed parameter tensors only. Modifications consist of supervised training of the decision head and last two encoder layers, described in `models/MODEL_CARD.md`. The base model is downloaded from its original host. A copy of Apache License 2.0 is in `models/LICENSE-APACHE-2.0.txt`.

## SMS Spam Collection

Almeida, T. and Hidalgo, J. (2012). *SMS Spam Collection*. UCI Machine Learning Repository. https://doi.org/10.24432/C5CC84

Licensed under [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). A 200-record subset and its use in evaluation records are redistributed with original message text, new JSON structure, and split metadata. No endorsement by the dataset authors is implied. The full original corpus is downloaded for training and is not checked in.

## Phishing and Benign Email Dataset

Creator: `darkknight25`; dataset card identifies **sunny thakur**. https://huggingface.co/datasets/darkknight25/phishing_benign_email_dataset

The pinned dataset card declares the MIT License. A copy of that card and the standard MIT license text are retained in `evals/licenses/`. Redistribution preserves the source attribution; the upstream card does not supply a dated copyright line. We redistribute a subset of subject, body, label, and identifier fields and add partition metadata.

## Fonts

**DM Sans** — Copyright 2014 The DM Sans Project Authors.

**Manrope** — Copyright 2019 The Manrope Project Authors.

Distributed through the `@fontsource-variable` packages under **SIL Open Font License 1.1**. Copies of the original license notices are retained in `docs/licenses/`. Fonts are served locally, without a third-party font request.

## Other dependencies

React, Vite, FastAPI, SQLite, Lucide, scikit-learn, PyTorch, Transformers, boto3, and development tools retain their respective upstream licenses. Dependency packages and lockfiles identify their versions and licenses. Lucide icons are used under ISC.
