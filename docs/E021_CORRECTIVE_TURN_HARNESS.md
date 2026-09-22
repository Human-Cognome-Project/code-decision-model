# E021 — Corrective-turn evaluation harness

The project's primary success criterion is not ranking accuracy. It is whether a small
local code generator paired with the decision layer needs materially fewer correction
turns than the same generator alone.

E021 establishes the measurement contract before attaching a real generator.

## Scope

This is an evaluation harness, not a general agent loop.

Each bounded episode has three replaceable components:

1. a generator produces one or more candidate artifacts for the current turn;
2. a selector chooses one candidate;
3. a deterministic validator decides whether the selected candidate satisfies the task.

The baseline selector accepts the generator's first candidate. The assisted condition can
use the code decision model over the same generated candidate set.

## Correction-turn definition

The initial generate/select/validate round is not a correction turn.

If the first selected candidate fails validation, the next generation round is correction
turn 1, and so on:

~~~text
attempted turns:   1  2  3
correction turns:  0  1  2
~~~

Task success is reported separately. A system that exhausts its turn budget does not
receive an artificial correction-turn advantage; paired correction deltas are only
reported when both conditions resolve the task.

## Paired design

Baseline and assisted conditions receive fresh generator instances from the same factory.
Later generator experiments should pin model revision, decoding parameters, and seed.

Different selected candidates may produce different deterministic validator feedback and
therefore different later generator trajectories. That divergence is part of the end-to-end
effect being measured.

## E021 gate

Before a real generator is attached, CPU-only tests require:

- first-pass success to equal zero correction turns;
- failure followed by success to count exactly one correction;
- an assisted selector to demonstrate a paired one-turn improvement on a scripted episode;
- unresolved-vs-resolved pairs to report success separately rather than invent a correction
  delta;
- invalid selector/scorer outputs to fail loudly.

## Next experiment

E022 should attach one compact open code generator and a deterministic code validator
(test, compile, or type-check outcome) to a pinned task corpus.

The comparison should hold generator revision, seed, decoding parameters, turn budget,
and validator constant. Only the candidate-selection/decision layer should differ.
