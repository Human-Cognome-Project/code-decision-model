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

Three post-replication mechanism results now sharpen that question:

- **E032 ranked re-recommendation:** on the original development repositories, replacing rejected evidence with the scorer's next feasible ranked recommendation improved success from 292/400 (73.0%) under E029 to 315/400 (78.75%). On wrong-first-recommendation tasks, recovery improved from 56/164 (34.1%) to 79/164 (48.2%), with exact McNemar p = 0.0128. This remains exploratory until the exact final intervention is replicated on the E031 independent repositories.
- **E033 call-expression intent:** a baseline-only 64-task validity pilot reached only 23/64 uniquely resolved/bindable calls and 2/64 exact repairs. The free-form call-expression surface is stopped for the pinned 0.5B generator.
- **E034 closed-vocabulary argument operations:** narrowing the output to one candidate plus one closed-vocabulary operation did not rescue Qwen 0.5B. Only 11/64 plans parsed, 2/64 were bindable, and 0/64 exactly repaired the call. All parsed plans were `candidate 1; keep`. Structured edit-intent generation is therefore stopped for this generator.

Active directions include:

- independent replication of the exact final E032 correction intervention on the E031 repository set;
- a materially more capable generator, under fresh preregistration, if structured edit-intent generation is revisited;
- replication with a second compact open generator;
- harder cross-file/LSP/compiler/type-checker decision tasks;
- repository-scale retrieval followed by decision reranking;
- calibrated escalation on unseen repositories;
- cheaper decision paths that preserve the end-to-end effect.

E029 rejection memory remains a useful control: it nearly eliminated repeated rejected choices but produced only a +0.75 pp end-to-end gain.

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
