# Experiments

## E001 — Can the separated-candidate primitive learn at all?

Before downloading or fine-tuning a pretrained code model, the smallest version should
demonstrate that gradients can teach the architecture a machine-verifiable code decision.

### Task

Python ASTs provide exact local call edges. For each top-level function that calls exactly
one other top-level function, construct:

- context: the caller source;
- question: which candidate function is directly called?;
- candidates: all top-level function signatures in the module;
- target: the callee identified by the AST.

No LLM labels are involved.

### Model

The E001 model intentionally uses the toy hashed-token encoder. Candidate representations are
still independent and cacheable.

### Pass condition

The model must reliably overfit a tiny deterministic set. Failure means the decision path or
training implementation is broken and there is no reason to try a larger encoder.

Passing E001 is **not** evidence that the architecture generalizes. The next useful experiment is
held-out generalization with a pretrained code encoder and larger machine-generated datasets.

Run:

```bash
python examples/learn_ast_calls.py
```

## E019 — Hard environmental constraints

See [E019_HARD_CONSTRAINTS.md](E019_HARD_CONSTRAINTS.md).

Adds a minimal interface so deterministic validators can veto or filter
candidates after neural scoring. Unique priors stay outside the model as
machine-checkable constraints; an empty surviving set produces an explicit
escalate signal.

## E021 — Corrective-turn repair harness

See [E021_CORRECTIVE_TURN_HARNESS.md](E021_CORRECTIVE_TURN_HARNESS.md).

Measures deterministic masked-call repair as a bounded baseline-vs-assisted
correction loop.

Companion example:
[E021_CORRECTIVE_TURN_MOCK.md](E021_CORRECTIVE_TURN_MOCK.md) exercises the
paired measurement path with deterministic mock generators and no model download.

## E022 — Open generator on the corrective-turn harness

See [E022_OPEN_GENERATOR_REPAIR.md](E022_OPEN_GENERATOR_REPAIR.md).

First live open-generator experiment on the E021 harness. Reserved for a pinned
real model; the mock path lives under E021.

### E022 live result

See [E022_LIVE_QWEN_RESULT.md](E022_LIVE_QWEN_RESULT.md).

The first pinned Qwen 0.5B pilot produced zero verified repairs in either arm.
The result is inconclusive for correction-turn reduction because the generator
did not cross the deterministic validity floor.

## E024 — Call-site bindability predicate

See [E024_CALL_SITE_PREDICATE.md](E024_CALL_SITE_PREDICATE.md).

First hard constraint derived from AST facts rather than substrings. Measures
what deterministic argument binding removes from masked-call decisions and
asserts it never vetoes the machine-labelled target.

Census:

```bash
python examples/census_call_site_predicate.py
```


## E023 — Structured-edit corrective turns

See [E023_STRUCTURED_EDIT.md](E023_STRUCTURED_EDIT.md).

Removes full-function generation. The generator emits only a candidate index;
deterministic code applies the edit. Measures whether fallible decision evidence
reduces wrong-selection correction turns.

The 12-task live pilot improved first-pass success from 2/12 to 7/12 and success
within two attempts from 5/12 to 8/12. This is a promising pilot and requires a
larger confirmatory held-out run.

## E026 — Paired corrective-turn statistics

See [E026_PAIRED_STATISTICS.md](E026_PAIRED_STATISTICS.md).

Reproducible aggregation of paired baseline/assisted outcomes from either
corrective-turn harness, with exact McNemar and sign tests and a source-clustered
bootstrap. Applied to the E023 pilot it gives p = 0.375 and p = 0.5, and sizes
the confirmatory run at roughly 30 to 60 held-out tasks depending on effect size.


## E025 — Full held-out structured-edit confirmation

See [E025_CONFIRMATORY_STRUCTURED_EDIT.md](E025_CONFIRMATORY_STRUCTURED_EDIT.md).

On the full 63-example held-out split, structured decision assistance increased
success within two attempts from 32/63 (50.8%) to 44/63 (69.8%). The paired
success-rate delta was +19.0 percentage points; exact McNemar p = 0.0428 and the
repository-stratified source-file bootstrap 95% interval was +2.7 to +32.8 points.

This confirms the E023 pilot on the current same-repository held-out split. The
next gate is unseen-repository replication.

## E027 — Unseen-repository holdout splits

See [E027_UNSEEN_REPOSITORY_SPLITS.md](E027_UNSEEN_REPOSITORY_SPLITS.md).

Adds the split the E025 next gate requires: held-out repositories go entirely
to test and all other repositories train by default, with an optional
source-disjoint retained validation split, a machine-checkable leakage guard, and
a leave-one-repository-out rotation whose
folds pool under E026 statistics.


### E027 live result

See [E027_LEAVE_ONE_REPOSITORY_OUT_RESULT.md](E027_LEAVE_ONE_REPOSITORY_OUT_RESULT.md).

Across all 400 examples in leave-one-repository-out rotation, success within two
attempts increased from 202/400 (50.5%) baseline to 289/400 (72.3%) assisted.
The paired micro delta was +21.75 percentage points; exact McNemar p ≈ 4.96e-12,
and the repository-stratified source-file bootstrap 95% interval was +14.37 to
+27.67 points. Every held-out repository fold was positive.

The next gate is development-independent replication on a second pinned repository
set. Current exploratory directions are tracked in
[OPEN_DIRECTIONS.md](OPEN_DIRECTIONS.md).


## E028 — Failure-conditioned structured-selection analysis

See [E028_FAILURE_CONDITIONED_ANALYSIS.md](E028_FAILURE_CONDITIONED_ANALYSIS.md).

Adds an analysis-only decomposition of remaining assisted failures into machine-counted mechanisms: wrong recommendations, ignored correct recommendations, failure to recover after deterministic feedback, and structured-output parse failures. It changes none of the frozen E027 protocol.


### E028 live result

See [E028_FAILURE_CONDITIONED_RESULT.md](E028_FAILURE_CONDITIONED_RESULT.md).

The preserved E027 task records show that the assisted generator followed the decision recommendation on 400/400 first attempts. Correct recommendations solved 236/236 tasks immediately; all 111 assisted terminal failures occurred after wrong recommendations. On the 164 wrong-recommendation tasks, success within two attempts was 80/164 baseline vs 53/164 assisted, with 20 second turns repeating the already-rejected recommendation. This motivates E029: deterministic rejection memory that removes a verifier-rejected candidate from the next-turn choice set.

## E029 — Deterministic rejection memory

See [E029_REJECTION_MEMORY.md](E029_REJECTION_MEMORY.md).

Motivated by E028: after the deterministic verifier rejects a candidate, remove that candidate from the next-turn choice set and remove any recommendation pointing to it. The intervention begins only after deterministic rejection; the live run preserves the exact historical E027 first-turn prompt. The experiment asks whether this hard correction-memory rule improves two-attempt success on wrong-recommendation tasks.

## E030 — Import-resolved cross-file call supervision

See [E030_CROSS_FILE_CALLS.md](E030_CROSS_FILE_CALLS.md).

First cross-file decision type under the existing integrity controls. Labels
come from deterministic resolution of module-level imports to top-level
functions in other repository files; no language server or model is involved.
The task is registered with the E021/E023 verifiers so the frozen E027 protocol
runs on it unchanged.

Census:

```bash
python examples/census_cross_file_calls.py
```


## E031 — Development-independent replication

See [E031_INDEPENDENT_REPLICATION_PREREG.md](E031_INDEPENDENT_REPLICATION_PREREG.md).

Preregisters the primary post-E027 validation gate before inspecting extraction density or model outcomes on the new repositories. Eight repositories are pinned in advance; the first four meeting a fixed extraction-only eligibility rule form the replication set. The primary run uses the frozen E027 same-file task, CodeRank + PairwiseMLP scorer, Qwen revision, two-attempt loop, and E026 paired statistics. E029 and E030 are explicitly excluded from the primary result.


### E031 extraction selection

See [E031_EXTRACTION_SELECTION.md](E031_EXTRACTION_SELECTION.md).

The preregistered extraction-only census found all eight candidates eligible. The fixed first-four rule therefore selects AlphaFold (26 tasks), Pyodide (53), Optuna (134), and pytest (208): 421 tasks across 108 source files. No scorer or generator result was inspected before this selection was fixed.

## E032 — Ranked feasible re-recommendation

See [E032_RANKED_REJECTION_MEMORY.md](E032_RANKED_REJECTION_MEMORY.md).

Extends E029: after a deterministic rejection, recommend the scorer's next
feasible candidate instead of nothing, and gate the first recommendation by hard
constraints. No new model call; the cached ranking is reused. Predicts recovery
on wrong-recommendation tasks near the scorer's conditional rank-2 accuracy.

Mock:

```bash
python examples/run_ranked_memory_mock.py
```
