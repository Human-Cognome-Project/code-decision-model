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
- **E032:** the live ranked-memory correction test improved success from 292/400 (73.0%) under E029 to 315/400 (78.75%). On 164 wrong-first-recommendation tasks, correction success rose from 56/164 (34.1%) to 79/164 (48.2%), +14.02 pp; exact McNemar p = 0.0128; clustered 95% CI +2.07 to +25.49 pp. This remains exploratory development-set evidence; replicate the exact frozen intervention on the E031 independent repositories before generalizing it.
- **E033:** call-expression intent reached only 36/64 parse-valid calls, 23/64 uniquely resolved/bindable calls, and 2/64 exact repairs in a baseline-only validity pilot. Stop this free-form call surface for the 0.5B generator; do not rescue it with permissive deterministic reconstruction.
- **E034:** the closed-vocabulary one-operation successor failed even earlier: 11/64 syntax-valid plans, 2/64 bindable plans, 0/64 correct operations, and 0/64 exact repairs. All 64 outputs anchored on candidate 1; all 11 parsed plans were `candidate 1; keep`. Stop structured edit-intent generation with the pinned Qwen 0.5B model. Do not prompt-tune, loosen the parser, or invent another schema on these 64 tasks.

Do not reinterpret or retune E031 after seeing its result. Do not tune the four E027 repositories merely to improve reported historical numbers.

## High-value directions

See [docs/OPEN_DIRECTIONS.md](docs/OPEN_DIRECTIONS.md).

Current high-value work includes:

- replicate the exact final E032 ranked-correction intervention on the E031 independent repository set without retuning;
- if structured edit-intent generation is revisited, use a materially more capable generator under a fresh preregistration; do not continue schema/prompt tuning with Qwen 0.5B;
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
- free-form repair generation without a deterministic measurement bridge;
- further Qwen 0.5B prompt/schema tuning on the E033/E034 validity-pilot tasks.

## How to work

1. Read `docs/ARCHITECTURE.md`, `docs/OPEN_DIRECTIONS.md`, and relevant `E0xx_*.md` files.
2. Check open PRs and active experiment workflows before choosing work.
3. Preserve the core invariants.
4. Keep the change small and testable.
5. Update result/provenance docs when the measurement changes.
6. In PR descriptions, state what would cause the direction to stop.

If a change would contaminate a frozen result or violate an invariant, do not submit it.
