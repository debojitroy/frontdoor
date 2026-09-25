# Contributing

FrontDoor welcomes improvements to the workbench, evaluation integrity, and model specialization.

Run the checks in the README before opening a pull request. Code changes should include behavioral tests where they protect data integrity, review persistence, inference boundaries, or reproducibility.

For model experiments, preserve existing evidence and write a separate candidate file. Include the training recipe, immutable base revision, split hashes, checkpoint selection rule, full per-case results, and failures. Never relabel a failing evaluation example or lower a quality threshold just to make a result pass.

New prompts or training changes after observing test results need a versioned development protocol and a new independently labeled holdout before making generalization claims. Keep related message variants in the same split.

Do not commit private messages, credentials, local databases, large weight files, or customer data. Open an issue to discuss new publicly licensed datasets.
