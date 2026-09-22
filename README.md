# Code Decision Model

Experimental local decision model for source-code reasoning.

## Hypothesis

A meaningful part of the correction burden in local coding assistants is **decision failure**, not generation failure.

Instead of asking a generative model to repeatedly reconstruct repository facts and then narrate a choice, this project tests whether a small code-focused discriminative model can answer runtime-defined questions directly.

The practical success criterion is:

> Does a small local code generator paired with this decision model require materially fewer corrective turns than the same generator alone?

## Architecture

Repository context, question, and every candidate are encoded independently:

```text
R   = encode(code context)
Q   = encode(question)
C_i = encode(candidate_i)

score_i = decision(R, Q, C_i)
P(i)    = softmax(score_i)
```

Candidate representations remain cacheable, and candidate count does not consume a shared prompt budget.

The frozen structured-selection protocol uses:

- `nomic-ai/CodeRankEmbed`;
- `PairwiseMLPScorer(hidden=32)`;
- independently cached candidate embeddings;
- `Qwen/Qwen2.5-Coder-0.5B-Instruct`;
- deterministic structured candidate selection and verification;
- greedy decoding;
- a two-attempt budget.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Current evidence

The strongest completed result is **E031**, the preregistered development-independent replication.

### E027 — development repositories

Across 400 leave-one-development-repository-out tasks:

| Metric | Baseline | Decision-assisted |
| --- | ---: | ---: |
| First-pass success | 101/400 (25.3%) | 236/400 (59.0%) |
| Success within two attempts | 202/400 (50.5%) | 289/400 (72.3%) |

Paired success-rate gain: **+21.75 percentage points**. Repository-stratified source-file bootstrap 95% CI: **+14.37 to +27.67 points**.

### E031 — independent replication

The frozen protocol was then preregistered and run on 421 tasks from AlphaFold, Pyodide, Optuna, and pytest, a repository set that did not influence architecture or protocol choices.

| Metric | Baseline | Decision-assisted |
| --- | ---: | ---: |
| First-pass success | 91/421 (21.6%) | 244/421 (58.0%) |
| Success within two attempts | 200/421 (47.5%) | 287/421 (68.2%) |

Paired success-rate gain: **+20.67 percentage points**. Exact McNemar p = **1.29e-11**. Repository-stratified source-file bootstrap 95% CI: **+13.97 to +27.46 points**. Every repository fold was positive.

See [docs/E031_INDEPENDENT_REPLICATION_RESULT.md](docs/E031_INDEPENDENT_REPLICATION_RESULT.md).

These results support the frozen structured-selection task. They are not claims about arbitrary free-form code repair.

## Current phase

Independent replication is complete. Current work asks what parts of the mechanism generalize beyond the original index-selection surface.

Active directions include:

- **E032 ranked re-recommendation:** after deterministic rejection, test whether the scorer's next feasible ranked choice improves recovery over E029's no-evidence correction turn;
- **E033 call-expression intent:** test whether a compact generator can emit actual Python call expressions under deterministic parse, membership, bindability, and AST-equivalence checks;
- replication with a second compact open generator;
- harder cross-file/LSP/compiler/type-checker decision tasks;
- repository-scale retrieval followed by decision reranking;
- calibrated escalation on unseen repositories;
- cheaper decision paths that preserve the end-to-end effect.

E029 rejection memory is retained as a useful control, but its live end-to-end gain was near-null: 289/400 to 292/400 (+0.75 pp).

See [docs/OPEN_DIRECTIONS.md](docs/OPEN_DIRECTIONS.md).

## Contributing

Humans and automated contributors are welcome.

Before starting work, read:

1. [AGENT.md](AGENT.md);
2. [CONTRIBUTING.md](CONTRIBUTING.md);
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md);
4. [docs/OPEN_DIRECTIONS.md](docs/OPEN_DIRECTIONS.md);
5. the relevant experiment notes under `docs/E0xx_*.md`.

New exploratory work should state its deterministic success/failure signal, comparison baseline, and stop/falsifier condition. Do not retune E027 or E031 test repositories merely to improve historical results.

## Run

```bash
python -m pip install -e ".[dev]"
pytest
```

Optional extras exist for specific encoders and live-generator experiments. Core tests remain CPU-runnable without model downloads.

## Status

Experimental research code. E031 is the current strongest confirmatory result; post-replication mechanism and generation-surface experiments are active.
