# E026 — Paired corrective-turn statistics

E023 produced the first positive end-to-end signal on the project's primary
criterion, from a 12-task pilot whose table was computed by hand. The
confirmatory run it calls for needs two things the repository did not have:

1. a reproducible aggregation of paired baseline/assisted outcomes into the
   standard report;
2. uncertainty and significance that remain honest at small sample sizes and
   under source-file clustering.

E026 adds both as `cdm.corrective`. It contains no model and changes no harness.

## What is measured

Both harnesses (E021 full-function repair, E023 structured edit) emit one paired
outcome per task. From a sequence of those:

| Quantity | Definition | Defined when |
| --- | --- | --- |
| success rate delta | assisted − baseline success within budget | always |
| mean attempts delta | baseline − assisted attempts within budget | always |
| correction-turn delta | baseline − assisted corrections | both arms resolve the task |

The correction-turn delta keeps the E021 rule: it is never fabricated for a task
one arm failed. Attempts within budget are reported as a separate, censored
burden measure, because a terminal failure counts the full budget and therefore
understates the true burden.

Group breakdowns by repository namespace and by function-vs-method task reuse
the `namespace::path` source convention.

## Exact paired tests

Two tests need no distributional assumption and stay valid at pilot sizes:

- **McNemar (exact)** on tasks resolved by exactly one arm.
- **Sign test (exact)** on unequal correction-turn deltas over paired successes.

Both are two-sided binomial tests at p = 1/2 over the discordant observations.

## Source-clustered bootstrap

Tasks from one source file share a caller pool and naming style. As in E012,
the bootstrap resamples files, not tasks, and each resampled task carries both
arms so the pairing is preserved. For E025, source files are sampled within
repository strata so repository composition is preserved. The conditional correction-turn statistic
skips resamples with no paired success and reports how many were kept.

## Applied to the E023 pilot

The pilot aggregates (4 both, 4 assisted-only, 1 baseline-only, 3 neither;
paired deltas of +1, +1, 0, 0) give:

- McNemar on 5 discordant tasks: p = 0.375
- sign test on 2 unequal deltas: p = 0.5

The pilot is consistent with a large effect and with no effect. That is the
quantitative form of "requires a larger confirmatory run".

## Sizing the confirmatory run

`discordant_pairs_for_significance` gives the smallest discordant count at which
the exact test rejects at α = 0.05, for an assumed favourable share:

| Favourable share of discordant tasks | Discordant tasks needed |
| ---: | ---: |
| 80% (the pilot's 4:1) | 12 |
| 75% | 17 |
| 70% | 25 |

In the pilot, 5 of 12 tasks were discordant. If that fraction holds, the run
needs about 29 tasks at the pilot's split, 41 at 75%, and 60 at 70%. The current
held-out test split has 63 examples, so the full split is enough only if the
effect is close to the pilot's size. A smaller true effect needs either more
held-out source groups or a second pinned repository set before a claim is made.

## Usage

```python
from cdm.corrective import (
    cluster_bootstrap_paired, exact_mcnemar, render_report, summarize_paired,
    summarize_paired_by, by_namespace, by_task,
)

summary = summarize_paired(outcomes)
print(render_report(summary))
interval = cluster_bootstrap_paired(
    examples,
    outcomes,
    statistic="success_rate_delta",
    strata=by_namespace,
)
by_repo = summarize_paired_by(examples, outcomes, by_namespace)
```

`render_report` prints the same table and paired-outcome list the E022 and E023
notes use, plus both exact tests.
