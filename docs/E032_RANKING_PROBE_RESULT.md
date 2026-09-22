# E032 — Frozen ranking probe result

E032 asks whether the decision scorer still contains useful residual information after its top choice is wrong. Before spending another live generator run, the frozen E027 scorer was recomputed on the original four development repositories and its full candidate ranking was measured.

No generator inference was used in this probe.

## Provenance

- workflow: `e032-ranking-probe`
- run: `35792012294`
- branch: `analysis/e032-ranking-probe`
- head SHA: `d89c530838eb4672f3200cfc871b2b8b887272f9`
- aggregate artifact: `e032-ranking-aggregate`
- artifact digest: `sha256:146125a0c37868a0f56c577565ff2733ca57e29da9bc55f0442a4f00bf51a51d`
- tasks: 400

The probe reproduced the frozen E027 top-1 decision result exactly: **236/400 correct (59.0%)**.

## Residual ranking signal

The top recommendation was wrong on 164 tasks.

On those tasks:

- the scorer's rank-2 candidate was correct on **77/164 (47.0%)**;
- after applying the E024 hard feasibility predicate, the first feasible recommendation changed on only one task;
- after that gating, 163 tasks still had a wrong first feasible choice;
- the next feasible ranked candidate was correct on **76/163 (46.6%)**.

This is materially above E029's observed correction-turn success on wrong-recommendation tasks, **56/164 (34.1%)**.

## Implied two-attempt ceiling

If the generator followed each feasible recommendation perfectly, E032 would solve:

- 237 tasks on the first feasible recommendation;
- 76 additional tasks on the next feasible recommendation;

for **313/400 (78.25%)** predicted two-attempt success.

For context:

| Condition | Success within 2 attempts |
| --- | ---: |
| Frozen E027 assisted | 289/400 (72.25%) |
| E029 rejection memory | 292/400 (73.00%) |
| E032 scorer-implied ceiling | 313/400 (78.25%) |

The ceiling is not a live result. It only establishes that the scorer contains enough residual signal to justify testing whether the generator can consume a second recommendation after deterministic rejection.

## Per-repository probe

| Repository | Top-1 correct | Rank-2 correct after top-1 wrong | Predicted two-turn successes |
| --- | ---: | ---: | ---: |
| browser-use | 133/210 | 43/77 | 176/210 |
| crawl4ai | 83/160 | 28/77 | 111/160 |
| markitdown | 11/17 | 3/6 | 14/17 |
| scrapling | 9/13 | 3/4 | 12/13 |

The useful residual signal is not confined to a single repository, although the two small folds are descriptive.

## Decision

The E032 cheap falsifier passes. Proceed to a live generator comparison on the original E027 development repositories only.

The live experiment should preserve the frozen first turn, apply deterministic rejection memory after a wrong selection, and compare:

- E029: no recommendation after rejection;
- E032: recommend the scorer's next feasible ranked candidate.

E032 should stop if the live ranked-memory arm does not materially improve on E029 within the same two-attempt budget, regardless of the scorer-only ceiling.
