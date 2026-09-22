# E028 — Failure-conditioned analysis result

E028 applies the failure-analysis surface to the preserved task-level records from
the completed E027 leave-one-repository-out run. No model or generator was rerun.

## Provenance

Source workflow:

- workflow: `e027-leave-one-repo-out`
- run: `35771855455`
- branch: `analysis/e027-leave-one-repo-out`
- head SHA: `8ec4530194884e187ace18d1ff81711e85f99e82`
- aggregate artifact: `e027-aggregate`
- artifact digest: `sha256:0dc409f935adc042a440154670f0c2da48ca75f393c06f799ff147d801de6edf`
- records analyzed: 400

The artifact contains the exact recommendation index plus every baseline and
assisted attempt trace for each task.

## Main result

The assisted generator followed the decision-model recommendation on the first
attempt in **400/400 tasks**.

That makes the mechanism unusually clear:

| Recommendation state | Tasks | Assisted first-pass success | Assisted success within 2 attempts |
| --- | ---: | ---: | ---: |
| Correct recommendation | 236 | 236/236 (100%) | 236/236 (100%) |
| Wrong recommendation | 164 | 0/164 (0%) | 53/164 (32.3%) |

There were no malformed structured outputs in the E027 records.

All **111 assisted terminal failures** therefore occurred on tasks where the
decision recommendation was wrong.

## What happened after a wrong recommendation

Every wrong recommendation was selected on the first assisted attempt.

On the second attempt:

- 53/164 selected the correct candidate;
- 20/164 repeated the already-rejected recommendation;
- 91/164 selected a different wrong candidate;
- 0/164 were unparseable.

So deterministic feedback recovered **32.3%** of wrong-recommendation tasks, but
failed on **67.7%**.

The repeated-recommendation cases show a specific anchoring failure: the verifier
had already rejected the candidate, but the same recommendation remained present
in the correction prompt.

## Paired comparison on wrong-recommendation tasks

The 164 tasks with a wrong decision recommendation are particularly informative,
because they isolate the cost of bad advice.

On those same tasks:

| Metric | Baseline | Assisted |
| --- | ---: | ---: |
| First-pass success | 39/164 (23.8%) | 0/164 (0%) |
| Success within 2 attempts | 80/164 (48.8%) | 53/164 (32.3%) |

Paired outcomes:

- both succeed: 42
- assisted only: 11
- baseline only: 38
- neither succeeds: 73

The assisted success-rate delta on this subset is **-16.5 percentage points**.

Exact McNemar on the 49 discordant tasks gives
**p ≈ 1.42 × 10⁻⁴**.

This is not evidence against the overall E027 intervention: E027 remains strongly
positive because correct recommendations are followed with extremely high
fidelity. It does show that a wrong recommendation is not merely neutral noise;
under the frozen prompt it materially harms the two-attempt outcome.

## Repository consistency

The wrong-recommendation recovery rate was similar in the two large folds:

| Held-out repository | Wrong recommendations | Assisted recovery | Baseline success on same tasks | Repeated rejected recommendation |
| --- | ---: | ---: | ---: | ---: |
| browser-use | 77 | 25/77 (32.5%) | 39/77 (50.6%) | 12/77 (15.6%) |
| crawl4ai | 77 | 24/77 (31.2%) | 34/77 (44.2%) | 8/77 (10.4%) |
| markitdown | 6 | 3/6 (50.0%) | 4/6 (66.7%) | 0/6 |
| scrapling | 4 | 1/4 (25.0%) | 3/4 (75.0%) | 0/4 |

The two small folds remain descriptive only.

## Interpretation

E028 falsifies two candidate explanations for the remaining E027 failures:

1. **Structured-output parsing is not the bottleneck.** There were no invalid
   choice-format attempts.
2. **Correct recommendations being ignored is not the bottleneck.** Correct
   recommendations were followed and solved on the first attempt in every case.

The dominant remaining failure path is instead:

1. decision model recommends the wrong candidate;
2. generator follows it;
3. deterministic verifier rejects it;
4. correction turn still operates under a prompt containing the now-discredited
   recommendation;
5. most tasks remain unresolved.

## Next experiment

E029 should test a hard correction-memory rule:

> once the deterministic verifier rejects a candidate, that candidate is removed
> from the next-turn choice set, and any recommendation pointing to it is removed
> with it.

This uses already-established verifier information as a hard environmental
constraint rather than adding another soft instruction.

The falsifier is straightforward: if deterministic rejection memory does not
improve success on wrong-recommendation tasks without changing first-pass
behavior, abandon this direction.
