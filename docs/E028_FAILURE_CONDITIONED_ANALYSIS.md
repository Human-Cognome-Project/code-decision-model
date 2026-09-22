# E028 — Failure-conditioned structured-selection analysis

E027 established a large corrective-burden gain, but aggregate success does not say where the assisted path still fails. E028 adds an analysis-only layer over already-recorded structured-selection outcomes.

It does **not** change the frozen E027 protocol: no scorer, prompt, generator, parser, attempt budget, split, or verifier behavior changes.

## Signals

For each assisted outcome, E028 records:

- whether the decision recommendation was correct;
- whether the first generator selection followed that recommendation;
- whether a correct recommendation was ignored on a terminal failure;
- whether a wrong recommendation was followed on a terminal failure;
- whether deterministic feedback failed to recover the task;
- whether failure began or ended as an unparseable selection.

The categories are deliberately orthogonal. One terminal failure can, for example, both follow a wrong recommendation and fail to recover after feedback.

## Why this matters

The next implementation choice should depend on which mechanism dominates:

- **wrong recommendation dominates** → improve the decision/retrieval side;
- **correct recommendation ignored** → improve how evidence is presented or consumed;
- **feedback recovery failure dominates** → improve the second-turn policy or deterministic intervention;
- **unparseable output dominates** → improve constrained decoding or the structured interface.

That gives each follow-up a falsifiable target instead of treating all failures as one bucket.

## API

```python
from cdm.failure_analysis import (
    failure_signature,
    render_failure_report,
    summarize_failures,
    summarize_failures_by,
)

summary = summarize_failures(examples, outcomes, recommendation_indices)
print(render_failure_report(summary))
```

Grouping is available through `summarize_failures_by` for repository or task-family analysis.

## Falsifier / stop rule

This direction is only useful if one or more failure mechanisms are concentrated enough to motivate a targeted intervention. If failure signatures are diffuse and unstable across repositories, do not optimize against them; keep the frozen replication gate primary.
