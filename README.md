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

The practical success criterion is:

> Does a small local code generator paired with this decision model require materially fewer corrective turns than the same generator alone?

## Architecture

The project separates repository context, question, and each candidate representation:

```text
R   = encode(code context)
Q   = encode(question)
C_i = encode(candidate_i)

score_i = decision(R, Q, C_i)
P(i)    = softmax(score_i)
```

Candidates are encoded independently, so repository and candidate representations remain cacheable and candidate count does not consume a shared prompt budget.

The current frozen end-to-end protocol uses:

- `nomic-ai/CodeRankEmbed`;
- `PairwiseMLPScorer(hidden=32)`;
- independently cached candidate embeddings;
- `Qwen/Qwen2.5-Coder-0.5B-Instruct` as the compact generator;
- deterministic structured candidate selection and verification rather than whole-function regeneration.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Current evidence

The experiment has progressed through deterministic AST supervision, hardened masked-call tasks, real code encoders, hard constraints, corrective-turn evaluation, and structured-edit selection.

The strongest result is **E027**, which evaluates each of four development repositories only in a fold where the decision scorer was trained on the other repositories.

Across 400 leave-one-repository-out examples:

| Metric | Baseline | Decision-assisted |
| --- | ---: | ---: |
| First-pass success | 101/400 (25.3%) | 236/400 (59.0%) |
| Success within two attempts | 202/400 (50.5%) | 289/400 (72.3%) |
| Terminal failures | 198/400 | 111/400 |

The paired success-rate gain was **+21.75 percentage points**. A repository-stratified source-file bootstrap gave a 95% interval of **+14.37 to +27.67 points**, and every held-out repository fold was positive.

This is evidence for the frozen structured-selection task, **not** a claim about arbitrary free-form code repair. See [docs/E027_LEAVE_ONE_REPOSITORY_OUT_RESULT.md](docs/E027_LEAVE_ONE_REPOSITORY_OUT_RESULT.md).

## Current phase

The primary validation gate is now **development-independent replication** on a second pinned repository set that has not influenced architecture, encoder choice, scorer shape, prompting, or thresholds.

The E027 protocol is to remain frozen before that result is observed.

Parallel exploratory work is welcome where it preserves deterministic measurement, including:

- cross-file/LSP/compiler-backed decision tasks;
- richer deterministic structured patch intents;
- repository-scale retrieval followed by reranking;
- hard deterministic constraints in the live loop;
- leaner decision paths that preserve the corrective-burden effect;
- calibrated escalation on unseen repositories;
- failure-conditioned analysis;
- later replication with a second compact generator.

See [docs/OPEN_DIRECTIONS.md](docs/OPEN_DIRECTIONS.md).

## Contributing

Humans and automated contributors are welcome.

Before starting work, read:

1. [AGENT.md](AGENT.md) — project invariants and current priorities;
2. [CONTRIBUTING.md](CONTRIBUTING.md) — contribution and testing rules;
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md);
4. [docs/OPEN_DIRECTIONS.md](docs/OPEN_DIRECTIONS.md);
5. the relevant experiment notes under `docs/E0xx_*.md`.

Do not retune the original four development repositories simply to improve E027. New exploratory work should state its deterministic success/failure signal and what result would falsify or stop the direction.

## Run

```bash
python -m pip install -e ".[dev]"
pytest
```

Optional extras exist for specific encoders and live-generator experiments. Core tests remain CPU-runnable without model downloads.

## Status

Experimental research code. E027 is the current strongest result; independent replication is the next primary gate.
