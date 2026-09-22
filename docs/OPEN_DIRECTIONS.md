# Open exploratory directions

This document is for agents and contributors looking for useful work after E027.
It is **not** a commitment to pursue every item. The current primary gate remains
development-independent replication on a second pinned repository set.

## Primary next gate

### Second pinned repository set

Select and pin a fresh set of repositories that has not influenced architecture,
encoder choice, scorer shape, prompting, or thresholds.

Before looking at the primary result:

- freeze the E027 Qwen revision and decoding;
- freeze the structured candidate-output parser;
- freeze the two-attempt budget;
- freeze the CodeRank + PairwiseMLP scorer recipe;
- predeclare E026 paired statistics;
- record repository revisions and extraction counts.

This is the highest-value near-term contribution.

## Exploratory directions

### Harder deterministic decision types

Move beyond same-file masked call recovery while preserving machine-verifiable
labels. Candidate sources include:

- LSP symbol/reference resolution;
- cross-file callable selection;
- type-checker or compiler diagnostic resolution;
- import/module selection;
- deterministic API compatibility checks;
- mutation/test outcomes.

A new task should have a clear verifier before model work begins.

### Structured patch intent

E022 showed that free-form whole-function regeneration can fail before the
decision layer is meaningfully tested. Explore intermediate edit forms richer than
a candidate index but still deterministic to apply and verify, for example:

- replace-symbol operations;
- argument insertion/removal/reordering;
- import edits;
- narrow AST rewrite templates.

The objective is to expand repair expressiveness without reintroducing an
uncontrolled text-generation bottleneck.

### Repository-scale candidate retrieval

The architecture assumes repository representations and candidate embeddings can
be cached. Test a two-stage path:

1. deterministic or embedding retrieval/shortlisting;
2. decision-model reranking over the shortlist.

Measure recall of the true candidate separately from decision accuracy and
end-to-end corrective burden.

### Deterministic constraints in the live loop

E019/E024 provide hard filtering machinery. Measure whether real AST/LSP/type
constraints improve the E027-style corrective loop when applied before the
generator sees the recommendation.

Report both candidate elimination and end-to-end effect; do not count filtering
alone as success.

### Leaner decision path

E016/E017 showed that representation quality matters more than merely shrinking
the scorer. Revisit cost only against the frozen end-to-end protocol:

- smaller encoders;
- quantized/static embeddings;
- lower-dimensional projections;
- simpler heads;
- cached repository representations.

A cheaper model is useful only if the corrective-burden effect is preserved.

### Confidence and escalation

E020 found that raw Potion cosine margin did **not** generalize as an escalation
signal. New confidence work should therefore use stronger held-out/OOD calibration
and should not simply retune the failed margin threshold.

Useful targets include:

- calibrated decision-head confidence;
- agreement between independent deterministic constraints and neural ranking;
- abstention criteria evaluated on unseen repositories.

### Failure-conditioned analysis

Use E027 records to characterize where assistance still fails:

- wrong decision recommendation;
- generator ignores a correct recommendation;
- second attempt fails after deterministic feedback;
- repository/task-family differences.

Analysis should produce a falsifiable next experiment rather than only taxonomy.

### Second generator replication

After the development-independent repository replication, repeat the frozen
decision intervention with another compact open generator. This tests whether the
effect depends on Qwen-specific instruction following.

Do not substitute generator swapping for the new-repository gate.

## Directions currently lower value

Avoid spending cycles on:

- larger decision heads without an end-to-end reason;
- more tuning on the existing four repositories;
- raw Potion-margin routing already falsified by E020;
- general agent loops;
- soft preferences or LLM-generated supervision where deterministic labels exist;
- free-form patch generation without a deterministic measurement bridge.

## Contribution rule

An exploratory PR should state:

1. which open question it tests;
2. what deterministic success/failure signal is used;
3. what existing result it is compared against;
4. what outcome would cause the direction to be abandoned.
