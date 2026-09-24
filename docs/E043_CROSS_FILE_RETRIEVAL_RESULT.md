# E043 — Cross-file repository retrieval result

E043 tested the preregistered retrieval-only first stage for E030 cross-file
calls on the pinned E031 repositories. The query was only the focused masked
caller context; module-level import text, target names, scorer outputs, and
E041/E042 ranks were excluded.

The fixed primary shortlist was 32 candidates.

## Population

The E030 extractor produced 265 retained tasks:

| Repository | Retained tasks |
| --- | ---: |
| AlphaFold | 0 |
| Pyodide | 3 |
| Optuna | 187 |
| pytest | 75 |
| **Total** | **265** |

There were no deterministic target-rendering ambiguity exclusions.

AlphaFold legitimately contributes no E030 tasks at its pinned revision. The
first live workflow treated an empty repository stratum as an error. E044's
independent census exposed that fact before the corrected run. The workflow was
changed only to preserve an empty stratum rather than fail; no retriever,
cutoff, query, population rule, or statistic changed.

Repository bindable pools on the retained tasks had mean 416.29 candidates,
median 389, and range 1–1,122.

## Preregistered primary result

| Retriever | Hits @32 | Recall @32 | Uniform expected hits | Mean excess | Clustered 95% CI, excess | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Potion 16M | 192/265 | 72.45% | 84.39 | +40.61 pp | +31.50 to +49.99 pp | **fail** |
| CodeRank | 224/265 | 84.53% | 84.39 | +52.68 pp | +43.91 to +61.14 pp | **pass** |

The fixed viability rule required both:

1. recall@32 >= 75%; and
2. clustered 95% CI lower bound for excess over uniform > 0.

Potion had strongly positive retrieval signal but missed the fixed recall floor.
CodeRank passed both conditions. The preregistered continuation is therefore to
use CodeRank retrieval in a separately preregistered frozen-reranker experiment
and record that the 16M static retriever was insufficient for this bounded
cross-file retrieval surface.

## Fixed-cutoff diagnostics

| Retriever | Recall @8 | Recall @16 | Recall @32 | Recall @64 | MRR |
| --- | ---: | ---: | ---: | ---: | ---: |
| Potion 16M | 58.11% | 63.77% | 72.45% | 80.75% | 0.407 |
| CodeRank | 73.96% | 80.38% | 84.53% | 86.79% | 0.566 |

At the primary cutoff, CodeRank recovered 163/187 Optuna tasks (87.2%), 1/3
Pyodide tasks, and 60/75 pytest tasks (80.0%). Potion recovered 154/187 Optuna,
1/3 Pyodide, and 37/75 pytest.

These per-repository figures are descriptive. Optuna contributes most of the
population, Pyodide is too small for a stable repository-specific estimate, and
AlphaFold contributes no E030 tasks.

## Interpretation

E043 establishes that a frozen independently encoded retrieval stage can reduce
the E030 repository decision to at most 32 candidates while retaining the
target on 84.5% of tasks under CodeRank context-to-candidate cosine.

It does **not** establish that the target can be selected correctly from that
shortlist. CodeRank's own rank-1 target count is 122/265 (46.0%), leaving a
large gap between retrieval recall and final selection. E045 tests whether the
already-frozen E031 PairwiseMLP can close part of that gap without any E030
training.

Potion is not promoted despite its much lower runtime because it failed the
predeclared 75% recall floor. No post-hoc cutoff is selected from the observed
rank distribution.

## Provenance

- preregistration: `docs/E043_CROSS_FILE_RETRIEVAL_PREREG.md`
- corrected live workflow run: `35967651191`
- live commit: `e13605c6c150a8f27ba0f4c510c76d1577e4b2cb`
- aggregate artifact: `10794493900`
- aggregate artifact digest:
  `sha256:75fbab49b258140610d6cbfae8175fffe3094fe3456d076cba1c5b0c8e6ce70c`
- bootstrap replicates: 5,000
- bootstrap seed: 43043
