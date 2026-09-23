# E036 — Canonical continuation likelihood pilot result

E036 tested whether the pinned Qwen 0.5B generator carried usable signal over
the finite E034 closed-vocabulary plan space even though E034 showed it could
not reliably emit a valid plan.

The preregistered baseline-only stop condition **was reached**. No paired
assisted E036 run should be performed on these 64 tasks.

## Provenance

- protocol: [E036_CONSTRAINED_PLAN_SCORING.md](E036_CONSTRAINED_PLAN_SCORING.md)
- live branch: `analysis/e036-canonical-likelihood-live`
- live commit: `a2af4521a5e74ec10ede458a8b93a33b0d5cd2f3`
- workflow run: `35864803103`
- aggregate artifact: `e036-aggregate`
- artifact id: `10751779988`
- artifact digest:
  `sha256:135c77efbc77c516cae8cc18a06902090c6ff13de2905df516c2401926fdd0b0`
- model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- revision: `ea3f2471cf1b1f0db85067f1ef93848e38e88c25`

The live workflow reproduced the exact E034 64-task sample-selection procedure:
stable hash, quota four per repository × task-family stratum, then global fill.
All four scoring shards and the aggregate completed successfully.

## Primary baseline-only result

The model-free uniform-over-binding-plans expectation on the frozen sample was
**12.32 exact tasks out of 64**.

Summed canonical continuation likelihood produced:

| Ranking | Exact |
| --- | ---: |
| Unrotated summed likelihood | 0/64 |
| Four-way cyclic-rotation summed likelihood | 10/64 |
| Uniform over E024-binding plans, expected | 12.32/64 |

Both summed-likelihood variants therefore remained at or below the
preregistered predicate-plus-uniform floor.

The literal stop check was true for both unrotated and rotated summed
likelihood. E036 stops here.

## Position-prior control

The unrotated top-plan candidate histogram was:

- candidate 1: 64;
- candidates 2–4: 0.

After cyclic rotation and mapping back to original candidates:

- candidate 1: 13;
- candidate 2: 13;
- candidate 3: 18;
- candidate 4: 20.

This confirms that the unrotated canonical ranking was dominated by the same
candidate-position prior exposed by E034, and that the rotation control largely
removed it.

## Secondary diagnostics

These were preregistered diagnostics and do not override the stop condition:

| Secondary ranking | Exact |
| --- | ---: |
| Unrotated length-normalized | 0/64 |
| Rotated length-normalized | 12/64 |
| Unrotated feasible-only summed | 16/64 |
| Rotated feasible-only summed | 19/64 |

The feasible-only secondary is above the raw uniform-over-binding expectation,
but E036 did not preregister it as the continuation gate. Using that secondary
post hoc to justify an assisted run would change the decision rule after seeing
the data.

On the 29 pure-selection tasks:

- unrotated summed likelihood: 0/29;
- rotated summed likelihood: 8/29;
- unrotated normalized: 0/29;
- rotated normalized: 10/29.

## Interpretation

Canonical continuation likelihood under a frozen prompt token boundary did not
clear the preregistered baseline-only floor. The free-generation failure in E034
therefore cannot be rescued by this canonical one-tokenization-per-plan ranking
procedure on the same 0.5B generator.

This remains distinct from exact grammar-constrained decoding or true plan MAP.
E036 scored one canonical token sequence per plan. It did not sum probability
over all admissible tokenizations.

Do not:

- run the paired assisted E036 arm on these 64 tasks;
- change the primary gate to the feasible-only secondary after inspection;
- retune rotation count, normalization, prompt wording, or tokenization on this
  sample;
- describe the method as exact constrained decoding.

If structured edit intent is revisited, follow the E034/E036 stop rule and
change generator capability or run a separately preregistered exhaustive
tokenization experiment rather than tuning this result.
