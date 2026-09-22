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

## Preferred contribution style

- Advance one clear experiment or close a measurement gap.
- Keep changes minimal and focused.
- Document new experiments in `docs/` with the existing `E0xx_NAME.md` pattern.
- Preserve the ability to run core tests on CPU without model downloads.
- Prefer open, compact encoders and adapters.

## High-value directions

- End-to-end corrective-turn evaluation harness.
- Clean interface for attaching hard deterministic constraints / validators that can veto or re-rank after neural scoring.
- Cross-file decisions under the same integrity controls used for same-file masked recovery.
- Further reduction of scorer capacity while preserving signal.
- Specialized, narrow need-expression models that emit precise intermediate forms for the decision layer.

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
