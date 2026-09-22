# E027 — Unseen-repository holdout splits

E025 confirmed the structured-edit corrective-burden effect on a held-out split
whose test files came from the same four repositories the scorer trained on.
Its stated next gate is replication on repositories the scorer never saw.

Every splitter in the repository so far (E003 hashed, E007 balanced, E009
namespace-stratified) deliberately places each repository in every partition.
That is the right design for a same-repository benchmark and the wrong one for
the next gate. E027 adds the missing split.

## Split

```text
held_out repositories       -> test, in full
every other repository      -> train, in full by default
optional retained validation -> source-disjoint inside each namespace when
                               explicitly requested
```

Nothing from a held-out repository is available for scorer training,
validation, or threshold selection. The default uses all non-held-out examples
for training because E027 freezes the E025 hyperparameters and performs no
validation selection. A non-zero retained-repository validation fraction remains
available for future protocols.

`verify_unseen_repository_split` is a machine-checkable guard: it raises if any
test namespace also appears in train or validation. A live run should call it
after loading the split, so the guarantee survives serialization.

## Rotation

`leave_one_repository_out` produces one unseen split per repository. Each task
is evaluated exactly once, by a scorer trained without its repository, and
paired outcomes can be pooled across folds. Reported with E026 statistics using
`strata=by_namespace`, the per-repository folds stay visible inside the pooled
interval.

## Two ways to satisfy the E025 gate

| Design | What it tests | Caveat |
| --- | --- | --- |
| Rotation over the four pinned repositories | transfer to a repository absent from scorer training | scorer hyperparameters (hidden size, seed, epoch count) were chosen while all four repositories were visible |
| A second pinned repository set, never used for development | the same, with no development leakage | requires a new corpus census and pinning |

The rotation is cheap and uses machinery already on main. It is the honest first
step, and its caveat should be stated in the result. The second design is the
stronger claim and should follow if the rotation holds.

## Fixed conditions the gate requires

Unchanged from E025: the Qwen revision, the structured-output protocol, the
two-attempt budget, deterministic supervision, and the predeclared E026
statistics. Only the split changes.

## Success signal

A pooled success-rate delta whose repository-stratified bootstrap interval
excludes zero, with a non-negative direction in each fold, would support the
architecture claim beyond the current same-repository split. A fold that goes
negative identifies repository-specific transfer as the next limiting factor,
which is also a useful result.
