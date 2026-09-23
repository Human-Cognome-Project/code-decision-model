# E039 — Decision-confidence routing result

E039 preregistered a first-turn routing test using only the frozen
PairwiseMLP decision head's top-class softmax probability.

The preregistered success-improvement gate **did not pass**.

## Provenance

- preregistration: [E039_CONFIDENCE_ROUTING_PREREG.md](E039_CONFIDENCE_ROUTING_PREREG.md)
- preregistration merge: `7399a423844642ff1c62b6554b7021bbaf764494`
- first live run: `35857190643` — aborted before threshold evaluation because
  the aggregate incorrectly assumed compact task identity fields were globally
  unique within a source file;
- infrastructure-only fix commit:
  `81fcddc2160dcde17fe2b001ab03da0dbda620ee`;
- corrected live run: `35860764911`;
- result artifact: `e039-result`;
- artifact id: `10749724648`;
- artifact digest:
  `sha256:5db792e6efbe74ba185990c02bcd68248c064b1fd4cab870248c77ac6796231e`.

The fix changed only the historical row-identity join: repeated compact
identities are aligned in deterministic extractor order and verified row by row.
The confidence feature, threshold grid, development fitting rule, E031
evaluation, and statistics were unchanged. The aborted run did not evaluate a
threshold or inspect an E031 routing result.

All eight corrected scorer jobs reproduced their frozen top-1 counts, and the
historical recommendation identities matched before routing outcomes were used.

## E027 threshold selection

The fixed threshold grid was `0.25, 0.30, ..., 0.95`.

The best E027 success count was 289/400 at both threshold 0.25 and threshold
0.35. Under the preregistered higher-threshold tie-break, E039 selected:

**threshold = 0.35**

At that threshold on E027:

- routed to assistance: 369/400;
- success within two attempts: 289/400;
- first-pass success: 235/400;
- mean attempts: 1.4125.

The complete threshold curve is retained in the result artifact.

## Independent E031 evaluation

The frozen 0.35 threshold routed:

- 385/421 tasks (91.4%) to assistance;
- 36/421 tasks (8.6%) to the historical baseline arm.

Primary outcome:

| Policy | Successes | Rate |
| --- | ---: | ---: |
| Always assist | 287/421 | 68.2% |
| Confidence route | 289/421 | 68.6% |

Paired gain: **+0.48 percentage points**.

Paired discordant outcomes:

- route only: 7;
- always-assist only: 5.

Exact two-sided McNemar p = **0.774**.

Repository-stratified source-file-clustered bootstrap 95% CI:
**-1.45 to +2.26 percentage points**.

The preregistered gate therefore failed two of three conditions:

1. positive pooled delta — passed;
2. McNemar p < 0.05 — failed;
3. clustered bootstrap lower bound > 0 — failed.

## Diagnostics

At the frozen threshold:

- recommendation accuracy among assisted tasks: 228/385 (59.2%);
- recommendation accuracy among abstained tasks: 16/36 (44.4%);
- routed first-pass successes: 239/421;
- routed mean attempts: 1.4323.

For comparison, always-assist E031 had:

- 244/421 first-pass successes;
- mean attempts 1.4204.

The threshold separated recommendation correctness somewhat, but not enough to
produce a reliable end-to-end success improvement.

The E031 sensitivity curve is retained as a diagnostic only. Some other
preregistered thresholds also happened to produce 289 successes, but none may
replace the E027-fitted threshold after inspection.

## Interpretation

Top-class softmax probability from the frozen PairwiseMLP head is **not**
supported as a success-improving first-turn routing signal under this protocol.

This does not weaken the decision ranking itself: E031, E035, E037, and E038
show that the ranking remains useful. E039 isolates a different question —
whether the head's raw top probability can decide when to expose the first
recommendation — and that simple routing feature did not transfer strongly
enough.

Stop this exact feature here. Do not retune the confidence transform, threshold
grid, or threshold on E031. A future escalation experiment should use a
meaningfully different preregistered signal rather than a post-hoc variant of
the same top-softmax threshold.
