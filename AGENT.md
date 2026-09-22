# Agent / Automated Contributor Guide

This repository is an experiment in a small, local, discriminative decision model for source-code reasoning. It is deliberately narrow.

## Core invariants

1. **Independent encoding**  
   Context, question, and each candidate are encoded separately. Candidate count must never consume a shared prompt/token budget. Repository and candidate representations must remain cacheable.

2. **Deterministic supervision preferred**  
   Prefer labels from parsers, ASTs, LSPs, type checkers, tests, mutation testing, or verified VCS outcomes. LLM-generated labels are last resort and must be clearly marked.

3. **Lean decision surface**  
   Keep the scoring head small relative to the encoder. Increase capacity only when an end-to-end measurement justifies it.

4. **No external theory or soft predicates**  
   Do not import broader project theory, narrative priors, or unverifiable preferences. Unique priors belong as hard machine-checkable constraints.

5. **Practical success criterion remains primary**  
   The key question is whether a compact generator plus this decision layer needs materially fewer corrective turns than the generator alone.

## Current experimental state

The strongest completed evidence is now **E031**, the preregistered development-independent replication.

- **E027:** on the four development repositories, success within two attempts improved from 202/400 (50.5%) to 289/400 (72.3%), +21.75 pp.
- **E028:** preserved traces showed the generator followed the recommendation on 400/400 first attempts; every remaining assisted terminal failure began with a wrong recommendation.
- **E029:** rejection memory reduced repeated rejected choices from 20 to 1 but changed success only from 289/400 to 292/400 (+0.75 pp; clustered 95% CI -0.96 to +2.32 pp). Treat this as a near-null end-to-end intervention.
- **E030:** deterministic import-resolved cross-file supervision is available as a harder task family.
- **E031:** on 421 tasks from AlphaFold, Pyodide, Optuna, and pytest, the frozen protocol improved success from 200/421 (47.5%) to 287/421 (68.2%), +20.67 pp; exact McNemar p = 1.29e-11; source-file clustered 95% CI +13.97 to +27.46 pp. The preregistered gate passed.
- **E032:** the scorer-ranking probe found rank 2 correct on 77/164 top-1 errors (47.0%), giving a scorer-implied two-turn ceiling of 313/400. The live post-rejection ranked-memory comparison is exploratory and separate from E031.
- **E033:** call-expression intent is merged. It is the first deterministic bridge from index selection to actual generated code fragments.

Do not reinterpret or retune E031 after seeing its result. Do not tune the four E027 repositories merely to improve reported historical numbers.

## High-value directions

See [docs/OPEN_DIRECTIONS.md](docs/OPEN_DIRECTIONS.md).

Current high-value work includes:

- finish and record the E032 live ranked-memory test;
- run E033 call-expression intent with the frozen compact generator and measure validity separately from correctness;
- replicate the frozen E031 intervention with a second compact open generator;
- extend deterministic supervision to harder cross-file/LSP/compiler/type-checker tasks;
- test repository-scale retrieval followed by decision reranking;
- revisit calibrated confidence/escalation on genuinely unseen repositories;
- reduce cost only when the corrective-burden effect survives.

## Contribution style

- Advance one clear experiment or close one measurement gap.
- State the deterministic signal, comparison baseline, and falsifier/stop condition.
- Keep changes focused.
- Add or update tests.
- Document experiment provenance and results.
- Preserve CPU-runnable core tests without model downloads.

## Avoid

- general agentic-loop expansion;
- soft unverifiable preferences;
- larger decision heads without an end-to-end reason;
- retuning E027 or E031 test sets;
- further prompt tuning of E029 after its near-null result;
- raw Potion-margin routing already falsified by E020;
- free-form repair generation without a deterministic measurement bridge.

## How to work

1. Read `docs/ARCHITECTURE.md`, `docs/OPEN_DIRECTIONS.md`, and relevant `E0xx_*.md` files.
2. Check open PRs and active experiment workflows before choosing work.
3. Preserve the core invariants.
4. Keep the change small and testable.
5. Update result/provenance docs when the measurement changes.
6. In PR descriptions, state what would cause the direction to stop.

If a change would contaminate a frozen result or violate an invariant, do not submit it.
