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

The development-independent replication gate was completed in E031. Current exploratory directions are tracked in [OPEN_DIRECTIONS.md](OPEN_DIRECTIONS.md).


## E028 — Failure-conditioned structured-selection analysis

See [E028_FAILURE_CONDITIONED_ANALYSIS.md](E028_FAILURE_CONDITIONED_ANALYSIS.md).

Adds an analysis-only decomposition of remaining assisted failures into machine-counted mechanisms: wrong recommendations, ignored correct recommendations, failure to recover after deterministic feedback, and structured-output parse failures. It changes none of the frozen E027 protocol.


### E028 live result

See [E028_FAILURE_CONDITIONED_RESULT.md](E028_FAILURE_CONDITIONED_RESULT.md).

The preserved E027 task records show that the assisted generator followed the decision recommendation on 400/400 first attempts. Correct recommendations solved 236/236 tasks immediately; all 111 assisted terminal failures occurred after wrong recommendations. On the 164 wrong-recommendation tasks, success within two attempts was 80/164 baseline vs 53/164 assisted, with 20 second turns repeating the already-rejected recommendation. This motivates E029: deterministic rejection memory that removes a verifier-rejected candidate from the next-turn choice set.

## E029 — Deterministic rejection memory

See [E029_REJECTION_MEMORY.md](E029_REJECTION_MEMORY.md).

Motivated by E028: after the deterministic verifier rejects a candidate, remove that candidate from the next-turn choice set and remove any recommendation pointing to it. The intervention begins only after deterministic rejection; the live run preserves the exact historical E027 first-turn prompt.

### E029 live result

See [E029_REJECTION_MEMORY_RESULT.md](E029_REJECTION_MEMORY_RESULT.md).

The intervention nearly eliminated immediate repetition of a rejected candidate but did not materially improve final success: 289/400 frozen assisted versus 292/400 with rejection memory (+0.75 pp), with a repository-stratified source-file bootstrap 95% interval of -0.96 to +2.32 pp. On wrong-recommendation tasks, paired McNemar p = 0.6072. E029 therefore fixes the narrow repetition symptom without a meaningful end-to-end gain.

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

### E031 live result

See [E031_INDEPENDENT_REPLICATION_RESULT.md](E031_INDEPENDENT_REPLICATION_RESULT.md).

The frozen protocol replicated on all 421 tasks: baseline success within two attempts was 200/421 (47.5%) and assisted success was 287/421 (68.2%), a paired gain of +20.67 percentage points. Exact McNemar p = 1.29e-11 and the repository-stratified source-file bootstrap 95% interval was +13.97 to +27.46 points. The preregistered confirmatory gate passed, and every repository fold was positive.

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

### E032 scorer-ranking probe

See [E032_RANKING_PROBE_RESULT.md](E032_RANKING_PROBE_RESULT.md).

The frozen E027 scorer reproduced 236/400 top-1 correct decisions. On its 164 top-1 errors, rank 2 was correct 77 times (47.0%). The scorer-implied two-turn ceiling is 313/400 (78.25%), compared with 292/400 observed under E029. This passes the cheap falsifier and justifies the separate live post-rejection ranked-memory test.

### E032 live ranked-memory result

See [E032_RANKED_MEMORY_LIVE_RESULT.md](E032_RANKED_MEMORY_LIVE_RESULT.md).

With the final correction prompt frozen as the unchanged E029 prompt plus the
exact historical recommendation sentence appended at the end, success within
two attempts increased from 292/400 (73.0%) under E029 to 315/400 (78.75%)
under E032. On the 164 wrong-first-recommendation tasks, correction success rose
from 56/164 (34.1%) to 79/164 (48.2%), a +14.02 pp gain. Exact paired McNemar
p = 0.0128 and the source-file-clustered bootstrap 95% interval for that subset
delta was +2.07 to +25.49 pp. The generator followed the second recommendation
on 156/164 correction turns.

This is exploratory development-set evidence. The exact final intervention
should be replicated without changes on the E031 independent repository set
before being treated as a general correction mechanism.

## E033 — Call-expression intent

See [E033_CALL_INTENT.md](E033_CALL_INTENT.md).

First structured edit richer than an index: the generator emits one Python call
expression, deterministic code splices it into the caller, and a four-stage
verifier (parse, candidate membership, E024 bindability, AST equivalence)
judges it with category-only feedback.

Mock and census:

```bash
python examples/run_call_intent_mock.py
python examples/census_call_intent.py
```

### E033 validity pilot

See [E033_CALL_INTENT_VALIDITY_RESULT.md](E033_CALL_INTENT_VALIDITY_RESULT.md).

A baseline-only, first-pass, 64-task pilot established the generation floor
before any paired experiment. The pinned Qwen 0.5B generator produced a
parseable call on 36/64 tasks (56.3%), a uniquely resolved and bindable call on
23/64 (35.9%), and the exact machine-labelled repair on only 2/64 (3.1%).
The invalid outputs were mostly genuine generation failures rather than harmless
formatting. E033 therefore stops at the validity gate for this generator and
surface; do not rescue it with permissive deterministic reconstruction of
missing calls or arguments.

## E034 — Closed-vocabulary argument operations

See [E034_ARGUMENT_OPERATIONS.md](E034_ARGUMENT_OPERATIONS.md).

Successor to the stopped E033 free-form call surface. The generator emits a
candidate index plus exactly one argument operation (keep, swap, drop, rename,
name, unname) whose identifier operands must come from a closed vocabulary:
call-site keywords plus parameter names visible in any candidate. The masked
call is perturbed deterministically and label-free, with the original as truth;
a four-stage verifier (parse and vocabulary, applicability, E024 bindability,
exact match) judges the plan. A model-free predicate-search baseline enumerates
the same candidate x operation plan space the parser admits, and a leakage
control checks that the visible corruption is invariant to relabelling.

Census:

```bash
python examples/census_argument_ops.py
```

### E034 baseline validity pilot

See [E034_VALIDITY_PILOT_PREREG.md](E034_VALIDITY_PILOT_PREREG.md) and
[E034_VALIDITY_PILOT_RESULT.md](E034_VALIDITY_PILOT_RESULT.md).

The preregistered 64-task baseline-only pilot failed the validity gate for the
pinned Qwen 0.5B generator. Only 11/64 outputs parsed as valid plans, 2/64
produced bindable edited calls, no output emitted the correct restoring
operation, and exact success was 0/64. Every output anchored on candidate 1; all
11 parsed plans were `candidate 1; keep`.

The deterministic predicate solved 0/64 tasks by itself, while 29/64 were
pure-selection cases with exactly one binding plan per candidate. E034
therefore stops this structured edit-intent surface for Qwen 0.5B. Do not run a
paired assisted E034 experiment or tune the schema/prompt on these pilot tasks.
A future edit-intent experiment should change generator capability under a
fresh preregistration.


## E035 — Independent replication of E032 ranked correction

See [E035_E032_INDEPENDENT_REPLICATION_PREREG.md](E035_E032_INDEPENDENT_REPLICATION_PREREG.md)
and [E035_E032_INDEPENDENT_REPLICATION_RESULT.md](E035_E032_INDEPENDENT_REPLICATION_RESULT.md).

E035 froze the final E032 post-rejection prompt and replicated it on the
preregistered E031 repository population without retuning. The scorer reproduced
the preserved E031 top-1 counts (244/421 correct), leaving 177
wrong-first-recommendation tasks.

On those 177 tasks, E029-style rejection-memory correction succeeded on 62
(35.0%) while ranked re-recommendation succeeded on 111 (62.7%), a +27.68 pp
gain. Exact McNemar p = 3.48e-7 and the repository-stratified
source-file-clustered bootstrap 95% interval was +17.65 to +37.16 pp. All three
preregistered replication gates passed.

Reconstructed overall two-attempt success was 306/421 (72.7%) with E029-style
memory and 355/421 (84.3%) with ranked re-recommendation. This upgrades the E032
mechanism from exploratory development evidence to an independently replicated
structured-selection result.

## E036 — Constrained plan scoring

See [E036_CONSTRAINED_PLAN_SCORING.md](E036_CONSTRAINED_PLAN_SCORING.md).

E034 showed the pinned generator cannot *emit* a closed-vocabulary plan. E036
asks whether it *knows* one: every plan in the E034 plan space is scored by the
generator's log-probability of its canonical token sequence (the plan text
tokenised on its own plus the end-of-turn token, after the frozen E034 prompt
tokens) and the best-scoring plan is taken. This is canonical continuation
likelihood ranking, not exact grammar-constrained decoding, which would sum
over every tokenisation of a plan. Format validity is 100% by construction; the question
becomes whether the likelihood ranks the restoring plan above chance and above
the model-free predicate-plus-ranker baseline. Corrective turns are
deterministic (drop the rejected plan, take the next). Label-free controls:
length normalisation and cyclic candidate rotation, which cancels the
candidate-1 position prior E034 exposed.

Mock (no download):

```bash
python examples/run_plan_scoring_mock.py
```

## E037 — Second-generator replication

See [E037_SECOND_GENERATOR_PREREG.md](E037_SECOND_GENERATOR_PREREG.md) and
[E037_SECOND_GENERATOR_RESULT.md](E037_SECOND_GENERATOR_RESULT.md).

The frozen E031 structured-selection intervention replicated with
HuggingFaceTB/SmolLM2-360M-Instruct at pinned revision
`cbcad7f4d160a10174f725b968ab6faf2a76399e`. Across the same 421 independent
tasks, success within two attempts increased from 113/421 (26.8%) baseline to
160/421 (38.0%) assisted, a paired gain of +11.16 pp. Exact McNemar p =
2.05e-9 and the repository-stratified source-file bootstrap 95% interval was
+7.74 to +14.42 pp, so all three preregistered replication gates passed.

SmolLM2 followed the first recommendation on only 181/421 tasks and assisted
first-turn parse validity was 305/421 (72.4%), so transfer occurred despite
substantially weaker prompt compliance than E031's Qwen run. Ranked
re-recommendation remains out of scope for E037 and may be tested separately.

## E039 — Decision-confidence routing

See [E039_CONFIDENCE_ROUTING_PREREG.md](E039_CONFIDENCE_ROUTING_PREREG.md).

Preregisters a selective-assistance test using only the frozen decision head's
top-class softmax probability. One threshold is selected on E027 from a fixed
0.25-to-0.95 grid using preserved paired generator outcomes, then evaluated
unchanged on preserved E031 paired outcomes. No generator is rerun and no E031
outcome participates in threshold selection.
