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

The strongest completed evidence now includes **E031**, the preregistered development-independent replication, and **E037**, its preregistered second-generator replication.

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

### E037 — second-generator replication

The same frozen E031 task, decision scorer, prompt/parser, verifier, and
two-attempt budget were run with `HuggingFaceTB/SmolLM2-360M-Instruct`.

| Metric | Baseline | Decision-assisted |
| --- | ---: | ---: |
| First-pass success | 80/421 (19.0%) | 124/421 (29.5%) |
| Success within two attempts | 113/421 (26.8%) | 160/421 (38.0%) |

Paired success-rate gain: **+11.16 percentage points**. Exact McNemar p =
**2.05e-9**. Repository-stratified source-file bootstrap 95% CI: **+7.74 to
+14.42 points**. The preregistered replication gate passed.

See [docs/E037_SECOND_GENERATOR_RESULT.md](docs/E037_SECOND_GENERATOR_RESULT.md).

These results support the frozen structured-selection task across two compact
open generator families. They are not claims about arbitrary free-form code
repair.

## Current phase

Independent replication is complete. Current work asks what parts of the mechanism generalize beyond the original index-selection surface.

Three post-replication mechanism results now sharpen that question:

- **E032/E035 ranked re-recommendation:** the development result improved wrong-recommendation recovery from 56/164 (34.1%) to 79/164 (48.2%). E035 then independently replicated the exact final intervention on the frozen E031 repositories: 62/177 (35.0%) under rejection memory versus 111/177 (62.7%) with ranked re-recommendation, +27.68 pp; exact McNemar p = 3.48e-7; clustered 95% CI +17.65 to +37.16 pp. Reconstructed overall success was 306/421 (72.7%) versus 355/421 (84.3%).
- **E033 call-expression intent:** a baseline-only 64-task validity pilot reached only 23/64 uniquely resolved/bindable calls and 2/64 exact repairs. The free-form call-expression surface is stopped for the pinned 0.5B generator.
- **E034 closed-vocabulary argument operations:** narrowing the output to one candidate plus one closed-vocabulary operation did not rescue Qwen 0.5B. Only 11/64 plans parsed, 2/64 were bindable, and 0/64 exactly repaired the call. All parsed plans were `candidate 1; keep`. Structured edit-intent generation is therefore stopped for this generator.
- **E037 second-generator replication:** with SmolLM2-360M-Instruct, success within two attempts increased from 113/421 (26.8%) to 160/421 (38.0%), +11.16 pp; exact McNemar p = 2.05e-9; clustered 95% CI +7.74 to +14.42 pp. The frozen structured-selection effect therefore transferred to a second generator family.

Active directions include:

- preregistered transfer of the independently replicated ranked-correction mechanism to SmolLM2;
- a materially more capable generator, under fresh preregistration, if structured edit-intent generation is revisited;
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

Experimental research code. E031 remains the main development-independent confirmatory result, and E037 independently extends the frozen structured-selection effect to a second compact generator family.
