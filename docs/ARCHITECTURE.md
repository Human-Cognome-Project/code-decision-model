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

## Phase 0 encoder

The first encoder is intentionally a trainable hashed-token mean pool. It is not expected to
be competitive. It exists to test interfaces, caching, data generation, and invariants without
network downloads or GPU requirements.

If the primitive behaves sensibly, replace it with a code-pretrained encoder and compare:

- GraphCodeBERT;
- UniXcoder;
- CodeT5/CodeT5+ encoder representations;
- a newer compact code embedding model if benchmarking justifies it.

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
