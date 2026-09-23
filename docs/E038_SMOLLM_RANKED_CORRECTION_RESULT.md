# E038 — SmolLM2 ranked-correction transfer result

E038 preregistered a conditional transfer test of the independently replicated
E032/E035 ranked post-rejection recommendation mechanism to
`HuggingFaceTB/SmolLM2-360M-Instruct`.

The preregistered three-part transfer gate **passed**.

## Provenance

- preregistration: [E038_SMOLLM_RANKED_CORRECTION_PREREG.md](E038_SMOLLM_RANKED_CORRECTION_PREREG.md)
- live workflow run: `35861568588`
- live commit: `fa46e6ddcf8512aced71b856a3bea02b41f24aba`
- generator revision: `cbcad7f4d160a10174f725b968ab6faf2a76399e`
- aggregate artifact: `e038-aggregate`
- artifact id: `10750508494`
- artifact digest:
  `sha256:8a2e2f1928af426c61aacfdff857399c073bdb95960d288fe0535434670a2368`

All four held-out-repository folds and the aggregate completed successfully.
The run reproduced the frozen 421-task extraction and decision-scorer top-1
counts before applying the historical E037 entry filter.

## Frozen conditional population

E038 used exactly the 77 preregistered E037 states where:

1. the scorer's first recommendation was wrong; and
2. SmolLM2 actually followed that wrong recommendation on its preserved first
   assisted turn.

The E037 second-turn outcome was not used for eligibility.

| Repository | Eligible tasks | Source files |
| --- | ---: | ---: |
| AlphaFold | 6 | 4 |
| Pyodide | 9 | 7 |
| Optuna | 20 | 11 |
| pytest | 42 | 23 |
| **Total** | **77** | **45** |

Task families were also reproduced exactly: 38 functions and 39 methods.

## Primary result

| Correction arm | Successes | Rate |
| --- | ---: | ---: |
| E029-style rejection memory | 11/77 | 14.3% |
| Ranked re-recommendation | 28/77 | 36.4% |

Paired correction-success gain: **+22.08 percentage points**.

Paired outcomes:

- both successful: 5;
- ranked only: 23;
- memory only: 6;
- neither: 43.

Exact two-sided McNemar p = **0.00232**.

Repository-stratified source-file-clustered bootstrap 95% CI for the paired
correction-success delta: **+9.21 to +35.21 percentage points**.

All three preregistered gate conditions therefore passed:

1. ranked correction success > rejection-memory success;
2. exact McNemar p < 0.05;
3. clustered bootstrap lower bound > 0.

## Recommendation signal and generator following

The scorer's next feasible ranked candidate was the machine-labelled target on
**55/77 (71.4%)** eligible tasks.

SmolLM2 followed that ranked recommendation on **38/77 (49.4%)** correction
turns.

Correction outputs were parse-valid on:

- 57/77 (74.0%) rejection-memory turns;
- 54/77 (70.1%) ranked-evidence turns.

The mechanism therefore transferred despite much weaker recommendation-following
than Qwen showed in E035.

## Repository breakdown

| Repository | Memory | Ranked | Delta successes |
| --- | ---: | ---: | ---: |
| AlphaFold | 0/6 | 3/6 | +3 |
| Pyodide | 0/9 | 7/9 | +7 |
| Optuna | 3/20 | 3/20 | 0 |
| pytest | 8/42 | 15/42 | +7 |

Three repositories were positive and Optuna was neutral. The preregistered gate
was pooled with source-file clustering and did not require every repository fold
to improve.

## Task-family breakdown

| Family | n | Memory | Ranked | Delta |
| --- | ---: | ---: | ---: | ---: |
| Functions | 38 | 5 | 18 | +34.21 pp |
| Methods | 39 | 6 | 10 | +10.26 pp |

Both task families moved in the same direction.

## Interpretation

E038 transfers the ranked post-rejection mechanism to a second compact generator
family **conditional on the generator having actually followed a wrong first
recommendation and received a deterministic rejection**.

This result does not reconstruct a 421-task end-to-end success rate, because
SmolLM2 did not deterministically follow first-turn recommendations in E037.
The claim is narrower: in the intended rejected-recommendation state, residual
decision ranking remains useful across generator families.

Together, E035 and E038 support ranked re-recommendation as a generator-transfer
mechanism for the frozen Python structured-selection task.

Do not retune SmolLM2 prompts, parser behavior, feasibility rules, scorer
settings, or the 77-task entry filter on this result.
