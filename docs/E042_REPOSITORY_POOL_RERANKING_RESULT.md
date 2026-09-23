# E042 — Repository-pool reranking result

E042 tested whether the frozen E031 decision scorer still carries useful target
ranking signal when the same held-out same-file function decisions are widened
from complete in-scope pools to complete E024-bindable repository pools.

The preregistered repository-pool gate **passed**.

## Provenance

- preregistration: [E042_REPOSITORY_POOL_RERANKING_PREREG.md](E042_REPOSITORY_POOL_RERANKING_PREREG.md)
- live branch: `analysis/e042-repository-pool-live`
- live commit: `df1e082ed94ee1395e983fa7d6fa18d03be7d55c`
- workflow run: `35895540692`
- aggregate artifact: `e042-aggregate`
- artifact id: `10768240513`
- artifact digest:
  `sha256:5cf54e87488e0d446b95e70ce26fd943c9b70a51ed6fdde2c4e8047c5acbe841`

All four held-out folds and the aggregate completed successfully.

## Continuity guards

Every fold reproduced both required historical guards before repository-pool
outcomes were interpreted:

| Held-out repository | E031 full-test guard | E041 scope-pool guard |
| --- | ---: | ---: |
| AlphaFold | 11/26 | 7/23 |
| Pyodide | 36/53 | 19/34 |
| Optuna | 87/134 | 26/79 |
| pytest | 110/208 | 30/86 |
| **Total** | **244/421** | **82/222** |

No training, predicate, or scope-pool drift was observed.

## Population

The source population was the frozen 222 E031 same-file function tasks.

Repository-level rendering ambiguity deterministically excluded 13 tasks:

- AlphaFold: 6;
- Pyodide: 1;
- Optuna: 6;
- pytest: 0.

Primary E042 population:

**209/222 tasks (94.14%)**

There were no target-absence or E024-target-veto integrity failures.

## Primary result

Complete E024-bindable repository pools had:

- mean size: **566.75 candidates**;
- median size: **483**;
- minimum: **76**;
- maximum: **1,122**.

The frozen scorer ranked the target first on:

**17/209 tasks (8.13%)**

The per-task predicate-plus-uniform baseline expected:

**0.607/209 successes (0.29%)**

Observed-minus-uniform mean excess:

**+7.84 percentage points**

Repository-stratified source-file-clustered bootstrap 95% CI:

**+4.46 to +11.85 percentage points**

Both preregistered gate conditions passed:

1. observed neural successes exceeded summed predicate-plus-uniform expectation;
2. the clustered bootstrap lower bound for mean excess was above zero.

## Repository folds

| Repository | Tasks | Neural top-1 | Uniform expected | Mean excess | Mean pool |
| --- | ---: | ---: | ---: | ---: | ---: |
| AlphaFold | 17 | 5 | 0.125 | +28.68 pp | 142.4 |
| Pyodide | 33 | 3 | 0.149 | +8.64 pp | 342.3 |
| Optuna | 73 | 3 | 0.204 | +3.83 pp | 424.4 |
| pytest | 86 | 6 | 0.129 | +6.83 pp | 857.6 |

Every repository fold had positive excess over its own uniform expectation.

## Rank diagnostics

Across all 209 retained tasks:

- mean reciprocal rank: **0.158**;
- target rank 1: **17**;
- top-3 recall: **32/209 (15.3%)**;
- top-5 recall: **45/209 (21.5%)**;
- top-10 recall: **65/209 (31.1%)**;
- top-20 recall: **93/209 (44.5%)**;
- top-50 recall: **134/209 (64.1%)**.

Pool-size bins:

| Bindable repository candidates | Tasks | Top-1 | Uniform expected |
| --- | ---: | ---: | ---: |
| 65–256 | 48 | 8 | 0.306 |
| >256 | 161 | 9 | 0.300 |

No retained repository task had fewer than 65 bindable candidates.

These diagnostics are descriptive and do not select a retrieval cutoff.

## Interpretation

E042 establishes that the frozen scorer's signal does not disappear when the
candidate set grows from four choices, to complete in-scope pools, to hundreds
of E024-bindable repository candidates. Raw top-1 accuracy falls sharply as the
choice set grows, but it remains far above the correct pool-size baseline.

This is evidence for repository-wide **ranking signal**, not for practical
repository-wide direct selection. The rank distribution shows why the next
architectural problem is retrieval or shortlisting: a bounded first stage must
preserve target recall before the frozen decision scorer reranks its output.

E042 does not justify:

- training on E041/E042 pool-expanded tasks;
- changing E024 or repository-pool construction on these repositories;
- choosing a shortlist cutoff post hoc from E042 rank diagnostics;
- exposing hundreds of repository indices directly to a generator.

The next retrieval experiment must report target recall separately from reranker
accuracy and end-to-end success.
