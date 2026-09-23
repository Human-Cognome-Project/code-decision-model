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

The completed confirmatory evidence now includes **E031**, the preregistered development-independent replication, plus **E037**, the preregistered second-generator replication.

- **E027:** on the four development repositories, success within two attempts improved from 202/400 (50.5%) to 289/400 (72.3%), +21.75 pp.
- **E028:** preserved traces showed the generator followed the recommendation on 400/400 first attempts; every remaining assisted terminal failure began with a wrong recommendation.
- **E029:** rejection memory reduced repeated rejected choices from 20 to 1 but changed success only from 289/400 to 292/400 (+0.75 pp; clustered 95% CI -0.96 to +2.32 pp). Treat this as a near-null end-to-end intervention.
- **E030:** deterministic import-resolved cross-file supervision is available as a harder task family.
- **E031:** on 421 tasks from AlphaFold, Pyodide, Optuna, and pytest, the frozen protocol improved success from 200/421 (47.5%) to 287/421 (68.2%), +20.67 pp; exact McNemar p = 1.29e-11; source-file clustered 95% CI +13.97 to +27.46 pp. The preregistered gate passed.
- **E032:** on the development repositories, ranked re-recommendation improved correction recovery from 56/164 (34.1%) under E029 memory to 79/164 (48.2%), +14.02 pp.
- **E035:** the exact final E032 intervention independently replicated on the frozen E031 repository set. On 177 wrong-first-recommendation tasks, correction recovery improved from 62/177 (35.0%) under E029 memory to 111/177 (62.7%), +27.68 pp; exact McNemar p = 3.48e-7; clustered 95% CI +17.65 to +37.16 pp. Reconstructed overall success was 306/421 (72.7%) vs 355/421 (84.3%). Treat ranked re-recommendation as an independently replicated mechanism on the structured-selection task.
- **E037:** with SmolLM2-360M-Instruct on the exact E031 population and frozen intervention, two-attempt success improved from 113/421 (26.8%) to 160/421 (38.0%), +11.16 pp; exact McNemar p = 2.05e-9; clustered 95% CI +7.74 to +14.42 pp. The preregistered gate passed despite first-turn recommendation following of only 181/421 (43.0%). Treat the base structured-selection effect as replicated across two compact generator families.
- **E038:** on the preregistered 77-task subset where SmolLM2 followed a wrong first recommendation, ranked correction improved success from 11/77 (14.3%) under rejection memory to 28/77 (36.4%), +22.08 pp; exact McNemar p = 0.00232; clustered 95% CI +9.21 to +35.21 pp. Treat ranked post-rejection evidence as transferred to a second compact generator family, conditional on entering the rejected-recommendation state.
- **E039:** E027 selected top-softmax threshold 0.35. On E031 it produced 289/421 successes versus 287/421 for always-assist, +0.48 pp; p = 0.774; clustered 95% CI -1.45 to +2.26 pp. The preregistered gate failed. Stop raw top-softmax confidence as a success-improving first-turn router; do not retune threshold or transform on E031.
- **E033:** call-expression intent reached only 36/64 parse-valid calls, 23/64 uniquely resolved/bindable calls, and 2/64 exact repairs in a baseline-only validity pilot. Stop this free-form call surface for the 0.5B generator; do not rescue it with permissive deterministic reconstruction.
- **E034:** the closed-vocabulary one-operation successor failed even earlier: 11/64 syntax-valid plans, 2/64 bindable plans, 0/64 correct operations, and 0/64 exact repairs. All 64 outputs anchored on candidate 1; all 11 parsed plans were `candidate 1; keep`. Stop structured edit-intent generation with the pinned Qwen 0.5B model. Do not prompt-tune, loosen the parser, or invent another schema on these 64 tasks.
- **E036:** canonical continuation likelihood on the exact 64 E034 tasks did not clear its baseline-only stop floor: 0/64 exact unrotated and 10/64 with cyclic rotation versus 12.32/64 expected under uniform choice over E024-binding plans. Do not run the paired assisted E036 arm or promote the 19/64 feasible-only secondary into a post-hoc gate. This was canonical one-tokenization-per-plan scoring, not exact constrained decoding.
- **E041:** the frozen E031 scorer transferred from four-way same-file function decisions to complete E024-bindable in-scope pools: 82/222 (36.9%) top-1 versus 27.73/222 (12.5%) expected under predicate-plus-uniform choice, +24.45 pp mean excess; clustered 95% CI +13.57 to +35.67 pp. All four repository folds were positive.
- **E042:** repository-pool scaling also passed. After 13 deterministic rendering-ambiguity exclusions, the frozen scorer achieved 17/209 (8.13%) top-1 over complete E024-bindable repository pools versus 0.607 expected successes (0.29%) under per-task uniform choice. Mean excess was +7.84 pp; clustered 95% CI +4.46 to +11.85 pp. Pools averaged 566.75 candidates, median 483, maximum 1,122. All E031/E041 continuity guards reproduced exactly. Treat repository-wide ranking signal as demonstrated, but not practical direct selection.

Do not reinterpret or retune E031 after seeing its result. Do not tune the four E027 repositories merely to improve reported historical numbers.

## High-value directions

See [docs/OPEN_DIRECTIONS.md](docs/OPEN_DIRECTIONS.md).

Current high-value work includes:

- **main line:** repository-scale retrieval/shortlisting followed by the frozen decision reranker; report retrieval target recall separately from reranker accuracy and do not choose a cutoff post hoc from E042;
- **encoder ablation:** CodeBERT/GraphCodeBERT is an open component-dependence experiment. Freeze task, head, training protocol, predicates, and split; change only the encoder. Treat it as exploratory unless run on a fresh preregistered population;
- **predicate infrastructure:** add independent machine-checkable constraints from LSP/type-checker/compiler/API/test facts, with labelled-target veto regression checks and fail-open handling of unknown information;
- if structured edit-intent generation is revisited, use a materially more capable generator under a fresh preregistration; do not continue schema/prompt tuning with Qwen 0.5B;
- revisit calibrated confidence/escalation only on a genuinely untouched population;
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
- raw PairwiseMLP top-softmax threshold routing already falsified as a transferable success-improving router by E039;
- free-form repair generation without a deterministic measurement bridge;
- further Qwen 0.5B prompt/schema tuning on the E033/E034 validity-pilot tasks;
- paired E036 assistance or post-hoc gate changes on the frozen 64-task canonical-likelihood pilot;
- training on E041/E042 pool-expanded evaluation tasks;
- post-hoc shortlist-size selection from E042 target-rank diagnostics.

## How to work

1. Read `docs/ARCHITECTURE.md`, `docs/OPEN_DIRECTIONS.md`, and relevant `E0xx_*.md` files.
2. Check open PRs and active experiment workflows before choosing work.
3. Preserve the core invariants.
4. Keep the change small and testable.
5. Update result/provenance docs when the measurement changes.
6. In PR descriptions, state what would cause the direction to stop.

If a change would contaminate a frozen result or violate an invariant, do not submit it.
