# E035 — Independent replication of E032 ranked correction: result

E035 preregistered a development-independent replication of the final E032
ranked re-recommendation mechanism on the frozen E031 repository set.

The preregistered three-part replication gate **passed**.

## Provenance

- workflow: `e035-e032-independent-replication`
- run: `35804195922`
- branch: `analysis/e035-e032-independent-replication`
- head SHA: `6513fb0df835db8c76c14ec8ac0558f24f0e256c`
- preregistration commit: `de8a9ce6edf7ab40499b7eb90304175535ed8fd7`
- aggregate artifact: `e035-aggregate`
- artifact digest: `sha256:40401bd932eae57afd4fdf6739355d802680439c00dd666d31d68cf94e5e6d4f`
- total E031 tasks: 421
- frozen scorer top-1 correct: 244
- wrong first recommendations evaluated: 177

All four folds reproduced the frozen E031 extraction counts and top-1 scorer
counts before correction outcomes were accepted. The generator reproduced the
wrong first recommendation on all 177/177 evaluated tasks.

## Primary result

On the 177 tasks where the frozen scorer's first recommendation was wrong:

| Correction arm | Successes | Rate |
| --- | ---: | ---: |
| E029 rejection memory | 62/177 | 35.0% |
| E032 ranked re-recommendation | 111/177 | 62.7% |

Paired correction-success gain: **+27.68 percentage points**.

Paired outcomes:

- both successful: 40;
- E032 only: 71;
- E029 only: 22;
- neither: 44.

Exact two-sided McNemar p: **3.48e-7**.

The preregistered repository-stratified, source-file-clustered bootstrap 95%
interval for the paired correction-success delta was **+17.65 to +37.16
percentage points**.

All three preregistered replication-gate conditions passed:

1. E032 ranked correction success > E029 memory success;
2. exact McNemar p < 0.05;
3. clustered bootstrap lower bound > 0.

## Reconstructed end-to-end success

Because the first turn is identical and the frozen scorer was correct on 244
tasks, the two correction mechanisms reconstruct to:

| Condition | Success within two attempts |
| --- | ---: |
| E029-style rejection memory | 306/421 (72.7%) |
| E032 ranked re-recommendation | 355/421 (84.3%) |

Overall gain: **+11.64 percentage points**.

This is not a comparison against the original E031 baseline arm; it isolates the
post-rejection correction mechanism after the same frozen assisted first turn.

## Recommendation signal and following

The next feasible ranked candidate was the labelled target on **117/177
(66.1%)** wrong-first-recommendation tasks.

The generator followed the second recommendation on **164/177 (92.7%)**
correction turns.

Ranked recovery reached 111/177, slightly below the 117-task scorer ceiling
because the generator occasionally did not follow a correct second
recommendation or followed a wrong one.

## Repository breakdown

| Repository | Wrong first recs | E029 memory | E032 ranked | Delta successes |
| --- | ---: | ---: | ---: | ---: |
| AlphaFold | 15 | 7 | 8 | +1 |
| Pyodide | 17 | 4 | 12 | +8 |
| Optuna | 47 | 17 | 34 | +17 |
| pytest | 98 | 34 | 57 | +23 |

Every repository fold moved in the same direction.

Reconstructed overall success by repository:

| Repository | E029-style | E032 ranked |
| --- | ---: | ---: |
| AlphaFold | 18/26 | 19/26 |
| Pyodide | 40/53 | 48/53 |
| Optuna | 104/134 | 121/134 |
| pytest | 144/208 | 167/208 |

AlphaFold remains too small for a strong fold-specific inference, but its
direction is consistent with the pooled result.

## Task-family breakdown

Among the wrong-first-recommendation tasks:

| Family | n | E029 memory | E032 ranked | Delta |
| --- | ---: | ---: | ---: | ---: |
| functions | 82 | 35 | 55 | +24.39 pp |
| methods | 95 | 27 | 56 | +30.53 pp |

Both task families show the same mechanism direction.

## Interpretation

E035 resolves the main uncertainty left by E032.

The final E032 development-set result was exploratory because its prompt was
finalized only after a prompt-order ambiguity had been discovered on the four
development repositories. E035 froze that final prompt and applied it without
retuning to the independent E031 repository population.

The mechanism replicated strongly:

> after a wrong first decision recommendation is deterministically rejected,
> the scorer's residual ranking contains useful information, and explicitly
> supplying the next feasible ranked candidate materially improves the compact
> generator's correction turn.

This is now stronger evidence than the original E032 development result.

The result also clarifies E029: rejection memory is useful as a correctness and
control mechanism, but the end-to-end gain comes from replacing rejected
evidence with fresh ranked evidence rather than merely removing the bad choice.

## Current status

Treat ranked re-recommendation as an independently replicated mechanism on the
frozen Python structured-selection task.

Do not retune E035 on the E031 repositories.

Remaining generalization questions include:

- another compact generator;
- harder deterministic decision types;
- repository-scale retrieval plus reranking;
- calibrated abstention/escalation;
- cheaper decision paths that preserve the replicated effect.

E033/E034 remain stopped for Qwen 0.5B structured edit-intent generation.
