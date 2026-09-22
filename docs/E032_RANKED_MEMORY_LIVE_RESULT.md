# E032 — Ranked re-recommendation live result

E032 tested whether useful scorer information remains after the frozen E027/E029
first recommendation has been rejected by the deterministic verifier.

The scorer-only probe justified a live test: on the 164 E027 tasks where top-1
was wrong, the labelled target was rank 2 on 77 tasks (47.0%).

## Final live protocol

The final live comparison preserves the E029 correction prompt exactly as a
prefix. E032 changes only one thing: after the E029 rejected-candidate feedback,
append the same historical recommendation sentence used by E027, now pointing to
the scorer's next feasible ranked candidate.

The first turn is the frozen E027 first turn. The candidate set after rejection
is the E029 candidate set. The attempt budget remains two.

Two earlier workflow attempts on the same analysis branch are **superseded
diagnostics**, not result-bearing runs:

- run `35794036463` placed the new recommendation before feedback containing
  "That candidate", creating an ambiguous reference;
- run `35794815727` fixed the ordering but used new explanatory recommendation
  wording.

The final run removes both confounds by appending the exact historical evidence
sentence after the unchanged E029 prompt.

## Provenance

- workflow: `e032-ranked-memory-live`
- final run: `35794865510`
- branch: `analysis/e032-ranked-memory-live`
- head SHA: `3042dfe592eb28c0a46dc48f7525140be3a47c11`
- aggregate artifact: `e032-live-aggregate`
- artifact digest: `sha256:ca3c5228b0cc5abc9e5111104ee515b3492d1b5b2d398a650c75efbc5f7e741b`
- tasks: 400
- wrong first recommendations: 164

The run reproduces the E029 control exactly before accepting the E032 comparison:
**56/164** successful correction turns under E029 memory.

## Result

| Condition | Success within 2 attempts |
| --- | ---: |
| Frozen E027 assisted | 289/400 (72.25%) |
| E029 rejection memory | 292/400 (73.00%) |
| E032 ranked re-recommendation | 315/400 (78.75%) |

Relative to E029, E032 adds **23 successful tasks**, an overall gain of
**+5.75 percentage points**.

On the 164 tasks affected by a wrong first recommendation:

| Correction condition | Successful |
| --- | ---: |
| E029 memory only | 56/164 (34.1%) |
| E032 next-ranked evidence | 79/164 (48.2%) |

Wrong-recommendation-subset gain: **+14.02 percentage points**.

Paired outcomes on those 164 tasks:

- both successful: 28;
- E032 only: 51;
- E029 only: 28;
- neither: 57.

Exact two-sided McNemar p: **0.0128**.

The repository-stratified, source-file-clustered bootstrap 95% interval for the
wrong-recommendation-subset delta is **+2.07 to +25.49 percentage points**.

Because all first-turn outcomes are identical between E029 and E032, the same
discordant pairs determine the overall paired comparison.

## Recommendation following

The generator followed the next feasible recommendation on **156/164 (95.1%)**
correction turns.

The scorer's next feasible recommendation itself was the labelled target on
**77/164** tasks. E032 nevertheless recovered **79/164** because two tasks were
solved when the generator did not follow an incorrect second recommendation.

This explains why the live result, 315/400, is two successes above the
scorer-only 313/400 ceiling that assumed perfect recommendation following.

## Repository breakdown

| Repository | E029 | E032 | Delta |
| --- | ---: | ---: | ---: |
| browser-use | 161/210 | 176/210 | +15 |
| crawl4ai | 106/160 | 112/160 | +6 |
| markitdown | 14/17 | 15/17 | +1 |
| scrapling | 11/13 | 12/13 | +1 |

All four development repositories move in the same direction, but the two small
folds are descriptive.

## Interpretation

E029 showed that merely removing a rejected choice almost eliminates repetition
without materially improving end-to-end success. E032 shows that replacing the
removed bad evidence with the scorer's next feasible ranked evidence produces a
measurable correction-turn benefit.

This supports a specific mechanism:

> the decision model contains useful residual ranking information after its
> first recommendation is wrong, and the compact generator can consume that
> information on a correction turn.

E032 remains **exploratory development-set evidence**. The final prompt was
frozen only after a prompt-order ambiguity was discovered on these same four
repositories. Do not tune it further here.

The next high-value gate is development-independent replication of this exact
final correction intervention on the already pinned E031 repository set, with no
prompt, scorer, parser, or attempt-budget changes.

The E031 confirmatory result remains the strongest evidence for the project's
core hypothesis.
