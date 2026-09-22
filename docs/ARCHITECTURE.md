# Architecture experiment

## Hypothesis

A substantial fraction of local coding-agent failure is decision failure rather than
generation failure. A small discriminative model may therefore improve a small generator
by handling repository-specific selection, ranking, and verification separately.

## Deliberate departure from Laya

Laya places the question, every candidate option, and state into a shared sequence. That is
efficient for small schemas, but candidate descriptions compete for a fixed token budget and
the state is re-encoded for each question.

This prototype separates three representations:

```
R = E(code context)
Q = E(question)
C_i = E(candidate_i)
score_i = D(R, Q, C_i)
```

Consequences:

1. candidate count does not consume a shared prompt head budget;
2. repository symbol/candidate embeddings can be cached;
3. code context can eventually be replaced by a persistent structural representation;
4. retrieval can reduce a repository-scale candidate set before discrimination;
5. the decision head remains independent of the particular encoder.

## Encoder history and current stack

The original Phase 0 encoder was a trainable hashed-token mean pool used only to
test interfaces, caching, data generation, and invariants.

Subsequent experiments evaluated real code encoders. The current frozen
end-to-end protocol uses:

- `nomic-ai/CodeRankEmbed` for context/question/candidate representations;
- a small `PairwiseMLPScorer(hidden=32)`;
- independently cached candidate embeddings;
- `Qwen/Qwen2.5-Coder-0.5B-Instruct` as the compact generator;
- structured candidate selection rather than whole-function regeneration.

E027 showed the corrective-burden effect survives leave-one-repository-out scorer
training across the four pinned development repositories.

Encoder/scorer changes are now exploratory cost or transfer questions, not the
primary validation gate. They should be compared against the frozen end-to-end
protocol rather than only ranking accuracy.

## Supervision ladder

Prefer labels generated from deterministic tools over model-generated labels:

1. parser / AST facts;
2. language-server symbol and reference facts;
3. compiler and type-checker diagnostics;
4. static call/data-flow analysis;
5. tests and mutation testing;
6. version-control patches and their verified outcomes;
7. human/model labels only where deterministic supervision is unavailable.

## Success criterion

The eventual experiment is not "does this classifier score well?"

It is:

> Does a small local generator paired with the decision model require materially fewer
> corrective turns than the same generator alone?

Everything else is an intermediate metric.


## Current validation frontier

The current strongest evidence is E027: across 400 leave-one-repository-out
examples, success within two attempts was 50.5% baseline vs 72.3% with decision
assistance.

The next primary gate is development-independent replication on a second pinned
repository set that has not influenced architecture or hyperparameter choices.

See:

- `docs/E027_LEAVE_ONE_REPOSITORY_OUT_RESULT.md`
- `docs/OPEN_DIRECTIONS.md`

Do not treat the current result as a claim about arbitrary free-form code repair.
The demonstrated task is structured candidate selection with deterministic
machine-labelled supervision and verification.
