# E018 — Batched cached-head training

The repository representation cache removes repeated encoder work, but the original
head-training loop still performed one optimizer step per decision.

E018 vectorizes the scorer path without changing the decision objective.

## Shapes

The scorers now accept either:

- one decision: context/question [D], candidates [K, D];
- a batch: context/question [B, D], candidates [B, K, D].

Pairwise features and cosine scores are computed over the final embedding dimension, so
the single-decision path remains unchanged.

## Variable candidate counts

No candidate padding or masked logits are introduced.

Cached examples are grouped by candidate count, then batched within each group. This
preserves the exact K-way cross-entropy for every decision while still vectorizing the
common fixed-cardinality case used by current experiments.

## Compatibility gate

Tests require:

- batched scorer logits to equal stacked single-decision logits;
- batched cross-entropy to equal the mean of individual losses;
- mixed candidate cardinalities to train without padding;
- cached batched training to make zero encoder calls;
- the tiny deterministic sanity task to remain learnable.

The existing per-example functions remain available as a reference path.
