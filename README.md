# Code Decision Model

Experimental local decision model for source-code reasoning.

## Hypothesis

A meaningful part of the correction burden in local coding assistants is **decision failure**, not generation failure.

Instead of asking a generative model to repeatedly reconstruct repository facts and then narrate a choice, this project tests whether a small code-focused discriminative model can answer runtime-defined questions directly:

- Which symbol owns this behavior?
- Which diagnostic is causal?
- Which candidate patch is relevant?
- Does this edit preserve a stated invariant?
- Which implementation satisfies this contract?
- Should the system act or escalate?

The eventual success criterion is deliberately practical:

> Does a small local code generator paired with this decision model require materially fewer corrective turns than the same generator alone?

## Why this is not just Laya-for-code

Laya demonstrated a useful typed-decision interface, but its current architecture puts the question, all options, and state into one sequence. That makes options compete for a fixed token budget and re-encodes state per question.

This experiment starts from a different primitive:

```text
R   = encode(code context)
Q   = encode(question)
C_i = encode(candidate_i)

score_i = decision(R, Q, C_i)
P(i)    = softmax(score_i)
```

The candidates are encoded independently. That permits:

- arbitrary runtime-defined choices;
- cached repository symbol representations;
- retrieval before discrimination for very large repositories;
- replacement of the toy encoder with a code-native pretrained encoder;
- eventual replacement of flat context with a persistent repository graph.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Current phase: architecture sanity check

The repository intentionally begins with a tiny trainable hashed-token encoder. It is **not intended to be a useful code model**. It exists so the data path, caching model, scoring head, and tests can run on CPU without model downloads.

The first machine-verifiable supervision uses Python AST facts. If the primitive survives basic experiments, the supervision ladder expands through LSP facts, compiler/type-checker diagnostics, static analysis, tests, mutation testing, and verified version-control outcomes.

## Run

```bash
python -m pip install -e ".[dev]"
pytest
```

## Status

Experimental. No performance claims yet.
