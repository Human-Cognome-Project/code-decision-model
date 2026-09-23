# E037 — Second-generator replication result

E037 preregistered a generator-dependence replication of the frozen E031
structured-selection intervention using
`HuggingFaceTB/SmolLM2-360M-Instruct` while holding the repository population,
decision scorer, prompt/parser, deterministic verifier, two-attempt budget, and
paired statistics fixed.

The preregistered confirmatory gate **passed**.

## Provenance

- preregistration: [E037_SECOND_GENERATOR_PREREG.md](E037_SECOND_GENERATOR_PREREG.md)
- live workflow run: `35855513250`
- live branch commit: `cb0fa59e60743c25b3c84bc34f9f688bc55b42b5`
- generator revision: `cbcad7f4d160a10174f725b968ab6faf2a76399e`
- aggregate artifact: `e037-aggregate`
- artifact id: `10749970897`
- artifact digest: `sha256:0789ae4ca0263ee4aa82f488c281121a92733bd488b7dee7475bb657bb870c39`

All four held-out-repository jobs and the aggregate job completed successfully.
The run reproduced the frozen E031 extraction counts and decision-scorer top-1
counts before accepting generator outcomes:

| Held-out repository | Tasks | Decision top-1 correct |
| --- | ---: | ---: |
| AlphaFold | 26 | 11 |
| Pyodide | 53 | 36 |
| Optuna | 134 | 87 |
| pytest | 208 | 110 |
| **Total** | **421** | **244** |

## Primary endpoint

Primary endpoint: success within two attempts.

| Metric | Baseline | Decision-assisted |
| --- | ---: | ---: |
| First-pass success | 80/421 (19.0%) | 124/421 (29.5%) |
| Success within two attempts | 113/421 (26.8%) | 160/421 (38.0%) |
| Terminal failures | 308/421 | 261/421 |
| Mean attempts | 1.810 | 1.705 |

Paired assisted-minus-baseline success-rate delta: **+11.16 percentage points**.

Paired outcome counts:

- assisted-only success: 56;
- baseline-only success: 9;
- both success: 104;
- neither success: 252.

Exact two-sided McNemar p = **2.05e-9**.

Repository-stratified source-file-clustered bootstrap 95% CI for the success-rate
delta: **+7.74 to +14.42 percentage points** (5,000 replicates, frozen seed
27027).

The preregistered gate therefore passed all three conditions:

1. assisted success > baseline success;
2. exact McNemar p < 0.05;
3. clustered bootstrap lower bound > 0.

## Repository results

| Held-out repository | Baseline success | Assisted success | Delta |
| --- | ---: | ---: | ---: |
| AlphaFold | 6/26 (23.1%) | 6/26 (23.1%) | 0.00 pp |
| Pyodide | 18/53 (34.0%) | 24/53 (45.3%) | +11.32 pp |
| Optuna | 27/134 (20.1%) | 48/134 (35.8%) | +15.67 pp |
| pytest | 62/208 (29.8%) | 82/208 (39.4%) | +9.62 pp |

The preregistered primary gate was pooled and clustered by source file within
repository; it did not require every repository fold to be positive. AlphaFold
was neutral at this sample size.

## Task-type results

| Task type | Baseline success | Assisted success | Delta |
| --- | ---: | ---: | ---: |
| Function | 63/222 (28.4%) | 91/222 (41.0%) | +12.61 pp |
| Method | 50/199 (25.1%) | 69/199 (34.7%) | +9.55 pp |

Both frozen task types therefore contributed positive pooled deltas.

## Generator diagnostics

SmolLM2 was materially less compliant with the frozen index-only prompt than
Qwen had been in E031:

- baseline first-attempt parse-valid: 368/421 (87.4%);
- assisted first-attempt parse-valid: 305/421 (72.4%);
- baseline second-attempt parse-valid: 332/341 (97.4%);
- assisted second-attempt parse-valid: 287/297 (96.6%);
- total invalid-format attempts: 62 baseline versus 126 assisted;
- assisted first-turn recommendation followed: 181/421 (43.0%).

The structured-selection effect therefore replicated despite substantially
weaker first-turn recommendation following and worse assisted first-turn format
validity. These diagnostics are secondary and do not change the preregistered
primary result.

## Interpretation

E037 establishes that the E031 structured-selection effect is not confined to
the pinned Qwen 0.5B generator. With a different compact open generator family,
the frozen decision layer still reduced two-attempt failure burden under the
same deterministic task and verifier.

The observed +11.16 pp effect is numerically smaller than E031's +20.67 pp Qwen
effect, but E037 did not preregister a formal between-generator effect-size test.
Do not interpret that numerical difference as a tested ranking of the
generators.

E037 does **not** test E032/E035 ranked post-rejection re-recommendation. Because
the base structured-selection intervention transferred, ranked-correction
transfer may now be preregistered separately as E038 without changing this
result.

Do not tune SmolLM2 on these 421 tasks to improve E037.
