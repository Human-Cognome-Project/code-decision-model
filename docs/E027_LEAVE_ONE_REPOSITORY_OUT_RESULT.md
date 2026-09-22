# E027 — Leave-one-repository-out replication

E027 tests whether the structured-edit corrective-burden effect survives when the
decision scorer has never trained on the repository being evaluated.

## Frozen protocol

Unchanged from E025:

- generator: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- revision: `ea3f2471cf1b1f0db85067f1ef93848e38e88c25`
- greedy structured selection
- strict full-response candidate parser
- maximum two attempts per arm
- `nomic-ai/CodeRankEmbed`
- `PairwiseMLPScorer(hidden=32)`
- seed 2
- one scorer-training epoch
- deterministic masked-call supervision

Each repository is evaluated exactly once, in the fold where all of its examples
are excluded from scorer training.

## Aggregate result

Across all 400 examples:

| Metric | Baseline | Assisted |
| --- | ---: | ---: |
| First-pass success | 101/400 (25.3%) | 236/400 (59.0%) |
| Success within two attempts | 202/400 (50.5%) | 289/400 (72.3%) |
| Terminal failures | 198/400 | 111/400 |
| Mean attempts, all tasks | 1.75 | 1.41 |

Paired outcomes:

- both succeed: 164
- assisted only: 125
- baseline only: 38
- neither succeeds: 73

The micro success-rate delta is **+21.75 percentage points**.

Exact McNemar on 163 discordant tasks gives **p ≈ 4.96 × 10⁻¹²**.

A 5,000-replicate source-file bootstrap, resampling within held-out repository
strata, gives:

- success-rate delta 95% interval: **+14.37 to +27.67 points**
- first-pass delta 95% interval: **+25.18 to +40.96 points**

## Per-repository folds

Every fold was positive:

| Held-out repository | Baseline | Assisted | Delta |
| --- | ---: | ---: | ---: |
| browser-use | 110/210 (52.4%) | 158/210 (75.2%) | +22.9 pp |
| crawl4ai | 75/160 (46.9%) | 107/160 (66.9%) | +20.0 pp |
| markitdown | 11/17 (64.7%) | 14/17 (82.4%) | +17.6 pp |
| scrapling | 6/13 (46.2%) | 10/13 (76.9%) | +30.8 pp |

The small markitdown and scrapling folds are descriptive only.

## Decision transfer

The fallible decision scorer achieved:

- micro accuracy: **59.0%**
- repository-macro accuracy: **62.3%**

The corrective-burden gain therefore does not depend on oracle recommendations.

## Correction turns among paired successes

Among the 164 tasks both arms solved:

- fewer assisted corrections: 60
- same corrections: 102
- more assisted corrections: 2
- mean baseline-minus-assisted correction delta: **+0.354 turns**
- exact sign-test p ≈ **8.47 × 10⁻¹⁶**

This is secondary to success within budget because the intervention changes which
tasks enter the paired-success subset.

## Interpretation

The E023/E025 effect survives leave-one-repository-out scorer training across the
four pinned development repositories.

The remaining caveat is developmental rather than fold leakage: these repositories
were known while the architecture, encoder, scorer shape, and protocol were being
developed.

## Next gate

Freeze the E027 protocol and evaluate a **second pinned repository set that has
not influenced architecture or hyperparameter choices**.

Do not retune the scorer, prompt, parser, attempt budget, or thresholds on that
new set before recording the primary result.
