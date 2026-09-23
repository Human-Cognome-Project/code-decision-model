# E041 — Scope-pool reranking result

E041 tested whether the frozen E031 decision scorer still carries useful ranking
signal when the four-candidate same-file function task is expanded to the
complete deterministic E040 E024-bindable in-scope pool.

The preregistered scope-pool gate **passed**.

## Provenance

- preregistration: [E041_SCOPE_POOL_RERANKING_PREREG.md](E041_SCOPE_POOL_RERANKING_PREREG.md)
- live branch: `analysis/e041-scope-pool-reranking-live`
- live commit: `727e32218d433d76e03edff8548e0f29a202cdcf`
- workflow run: `35876430433`
- aggregate artifact: `e041-aggregate`
- artifact id: `10758956541`
- artifact digest:
  `sha256:a1239a79e60ebd5868b40b5f94eab8e2a0519b81626141cde3f6c7e72f2f268e`

All four held-out-repository jobs and the aggregate completed successfully.

Each fold reproduced the frozen E031 full-test scorer top-1 count before any
pool result was accepted:

| Held-out repository | E031 guard |
| --- | ---: |
| AlphaFold | 11/26 |
| Pyodide | 36/53 |
| Optuna | 87/134 |
| pytest | 110/208 |
| **Total** | **244/421** |

The frozen E031 same-file function population also reproduced exactly:
23 + 34 + 79 + 86 = **222 tasks**.

There were **zero deterministic ambiguity exclusions**, so the E041 primary
population remained all 222 tasks.

## Primary result

The widened bindable scope pools had:

- mean size: **11.43 candidates**;
- median size: **8**;
- minimum: **4**;
- maximum: **42**.

The frozen scorer selected the target top-1 on:

**82/222 tasks (36.9%)**

The per-task predicate-plus-uniform baseline,
`sum_i 1 / pool_size_i`, expected:

**27.73/222 successes (12.5%)**

Observed-minus-uniform mean excess:

**+24.45 percentage points**

Repository-stratified source-file-clustered bootstrap 95% CI:

**+13.57 to +35.67 percentage points**

Both preregistered gate conditions passed:

1. observed top-1 successes exceeded the summed predicate-plus-uniform
   expectation;
2. the clustered bootstrap lower bound for mean excess was above zero.

## Repository folds

| Repository | Tasks | Neural top-1 | Uniform expected | Mean excess |
| --- | ---: | ---: | ---: | ---: |
| AlphaFold | 23 | 7 | 3.83 | +13.80 pp |
| Pyodide | 34 | 19 | 4.08 | +43.89 pp |
| Optuna | 79 | 26 | 8.83 | +21.74 pp |
| pytest | 86 | 30 | 10.99 | +22.10 pp |

Every held-out repository had positive excess over its own
predicate-plus-uniform expectation. Per-repository direction was descriptive,
not part of the preregistered pass gate.

## Effect of widening from four candidates

On the same 222 E031 function tasks, the original four-candidate scorer got:

**140/222 (63.1%) top-1**

At complete bindable scope scale it got:

**82/222 (36.9%) top-1**

Absolute top-1 accuracy therefore falls as expected when the candidate set is
expanded, but the decision signal remains far above the correct pool-size
baseline rather than collapsing toward uniform choice.

This distinction is important: E041 supports **ranking transfer to the real
in-scope decision**, not invariance of raw accuracy to candidate count.

## Rank diagnostics

Across all 222 pool-scale tasks:

- mean reciprocal rank: **0.579**;
- target ranked first: **82**;
- target ranked second: **51**;
- target ranked third: **35**;
- top-3 target recall: **168/222 (75.7%)**.

For tasks whose pools were large enough for the corresponding cutoff:

- top-5: 175/201 (87.1%);
- top-10: 89/98 (90.8%).

Pool-size bins:

| Bindable candidates | Tasks | Top-1 | Uniform expected |
| --- | ---: | ---: | ---: |
| 2–4 | 21 | 13 | 5.25 |
| 5–8 | 92 | 28 | 14.69 |
| 9–16 | 74 | 31 | 6.35 |
| >16 | 35 | 10 | 1.44 |

No task had a one-candidate pool.

These are descriptive diagnostics only; E041 does not select a shortlist size
or pool cutoff from them.

## Interpretation

E041 shows that the frozen scorer's four-candidate result is not merely an
artifact of being handed an already tiny choice set. On held-out repositories,
the same independently trained scorer retains substantial target-ranking signal
over the complete deterministic E024-bindable in-scope pool.

The result also defines the next boundary cleanly. E041 tested scope pools only.
It does **not** establish that direct ranking survives the much larger
repository-level pools measured by E040. Under the preregistered continuation
rule, repository-pool scaling must be a separate experiment.

Do not train on these pool-expanded E031 tasks or tune the scorer, pool
definition, bindability predicate, or candidate-size cutoff on this result.
