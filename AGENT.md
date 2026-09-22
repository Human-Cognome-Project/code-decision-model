# Agent / Automated Contributor Guide

This repository is an experiment in a small, local, discriminative decision model for source-code reasoning. It is deliberately narrow.

## Core invariants (do not break)

1. **Independent encoding**  
   Context, question, and each candidate are encoded separately. Candidate count must never consume a shared prompt/token budget. Repository and candidate representations must remain cacheable.

2. **Deterministic supervision preferred**  
   Prefer labels from parsers, ASTs, LSPs, type checkers, tests, mutation testing, or verified VCS outcomes. LLM-generated labels are last resort and must be clearly marked.

3. **Lean decision surface**  
   The scoring head should stay small relative to any encoder. Prefer simple, inspectable scorers (including very low-parameter variants) unless a clear measurement shows otherwise.

4. **No external theory or soft predicates**  
   Do not import physics, cosmology, broader project narratives, or unstated philosophical constraints. Unique priors belong as hard, machine-checkable environmental constraints, not as prompt text or soft preferences inside the model.

5. **Practical success criterion remains primary**  
   The ultimate test is whether a small local generator + this decision model needs materially fewer corrective turns than the generator alone. Intermediate ranking metrics are useful only insofar as they serve that goal.

## Current experimental state

The current strongest result is E027.

- E022: full-function generation with the pinned Qwen 0.5B model did not cross the deterministic validity floor.
- E023: structured edit intent produced the first positive 12-task corrective-burden pilot.
- E025: the effect was confirmed on the full 63-example same-repository held-out split.
- E027: leave-one-repository-out scorer training across all 400 examples produced 50.5% baseline vs 72.3% assisted success within two attempts. The paired micro gain was +21.75 percentage points; the repository-stratified source-file bootstrap 95% interval was +14.37 to +27.67 points, and every repository fold was positive.

The next primary gate is **development-independent replication on a second pinned repository set that has not influenced architecture or hyperparameter choices**.

Do not retune the existing four repositories simply to improve E027. See
`docs/E027_LEAVE_ONE_REPOSITORY_OUT_RESULT.md` and
`docs/OPEN_DIRECTIONS.md`.

## Preferred contribution style

- Advance one clear experiment or close a measurement gap.
- Keep changes minimal and focused.
- Document new experiments in `docs/` with the existing `E0xx_NAME.md` pattern.
- Preserve the ability to run core tests on CPU without model downloads.
- Prefer open, compact encoders and adapters.

## High-value directions

The authoritative current list is [docs/OPEN_DIRECTIONS.md](docs/OPEN_DIRECTIONS.md).

Highest priority:

- development-independent replication on a second pinned repository set;
- harder machine-verifiable decision types, especially cross-file/LSP/compiler-backed tasks;
- structured patch intents that remain deterministic to apply and verify;
- repository-scale retrieval followed by decision reranking;
- live-loop use of hard deterministic constraints;
- cost reduction only when the frozen corrective-burden effect is preserved.

Exploratory work should state what result would falsify or stop the direction.

## Low-value / avoid

- Expanding into general agentic loops.
- Adding soft ranking preferences that cannot be checked.
- Increasing model capacity without a corresponding end-to-end measurement.
- Broad multi-task supervision before the constraint interface and corrective-turn loop exist.

## How to work

1. Read `docs/ARCHITECTURE.md` and the relevant `E0xx_*.md` files.
2. Keep the change set small.
3. Add or update tests.
4. Update experiment documentation if you introduce new measurements or controls.
5. In the PR description, explicitly state which invariant(s) you preserved and which success criterion or experiment the change advances.

If a change would violate any core invariant, do not submit it.
