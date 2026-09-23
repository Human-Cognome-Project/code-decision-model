# E039 — Decision-confidence routing preregistration

E028 showed that a wrong first recommendation is harmful because the compact
generator follows it with very high fidelity. E035 showed that residual ranking
helps after rejection. E039 asks a different question:

> Can the trained decision head identify, before the first generator turn, when
> its own top recommendation should be withheld?

E020 already falsified raw Potion cosine margin as a useful general routing
signal. E039 does not revisit that feature. It tests the frozen PairwiseMLP
decision head's own top-class softmax confidence.

No new generator call is needed. The historical E027 and E031 experiments
already contain paired deterministic baseline and assisted trajectories for
every task. Once a confidence threshold is fixed, the routing policy selects
one of those already-observed arms task by task.

This document freezes the confidence feature, threshold search, development set,
independent evaluation set, outcome construction, and statistics before any E039
decision-score confidence is inspected.

## Confidence feature

For one task, let the frozen decision scorer produce four logits.

Define:

`confidence = softmax(logits)[argmax(logits)]`

using the scorer's float logits before any generator call.

No temperature fitting, Platt scaling, isotonic regression, rank-gap feature, or
other calibration transform is allowed in E039.

The recommendation itself remains the raw top-1 candidate.

## Development set — E027 only

Fit the routing threshold only on the 400 E027 development-repository tasks:

- browser-use: 210;
- crawl4ai: 160;
- markitdown: 17;
- scrapling: 13.

Use the exact pinned repositories, extractors, CodeRank encoder, PairwiseMLP
head, leave-one-repository-out training, focus transform, seed, epoch, optimizer,
and candidate order from E027.

The reproduced top-1 correctness counts must be:

| Repository | Correct | Tasks |
| --- | ---: | ---: |
| browser-use | 133 | 210 |
| crawl4ai | 83 | 160 |
| markitdown | 11 | 17 |
| scrapling | 9 | 13 |
| **Total** | **236** | **400** |

Any reproduction drift invalidates the score collection.

Historical paired outcomes come from the preserved E027 aggregate artifact:

- workflow run: `35771855455`;
- artifact: `e027-aggregate`;
- artifact digest:
  `sha256:0dc409f935adc042a440154670f0c2da48ca75f393c06f799ff147d801de6edf`.

No E027 generator is rerun.

## Threshold selection

Candidate thresholds are fixed in advance:

`0.25, 0.30, 0.35, ..., 0.90, 0.95`.

For a threshold `t`:

- if `confidence >= t`, select that task's historical **assisted** trajectory;
- otherwise select that task's historical **baseline** trajectory.

For each threshold, count success within two attempts on all 400 E027 tasks.

Choose the threshold with the greatest number of successes.

Tie-break, in order:

1. the **higher threshold** (less recommendation exposure);
2. no other criterion.

This is the only fitted E039 parameter.

Record the complete E027 threshold curve before evaluating E031.

## Independent evaluation — E031

After the threshold is fixed, evaluate it unchanged on the 421 frozen E031
independent-repository tasks:

- AlphaFold: 26;
- Pyodide: 53;
- Optuna: 134;
- pytest: 208.

Use the exact E031 scorer protocol. Reproduced top-1 correctness must be:

| Repository | Correct | Tasks |
| --- | ---: | ---: |
| AlphaFold | 11 | 26 |
| Pyodide | 36 | 53 |
| Optuna | 87 | 134 |
| pytest | 110 | 208 |
| **Total** | **244** | **421** |

Historical paired outcomes come from the preserved E031 aggregate:

- workflow run: `35789900382`;
- artifact: `e031-aggregate`;
- artifact digest:
  `sha256:fe17974a3a1e1d75f20cb10343dc501f7dd2affd80946c2272cacbc5dacf2951`.

No E031 generator is rerun.

For each task, the frozen E027-fitted threshold selects either its historical
E031 baseline trajectory or its historical E031 assisted trajectory.

Because both historical arms used greedy decoding and the same deterministic
two-attempt verifier, this is a direct replay of the routing policy rather than
a newly sampled generator outcome.

## Primary comparison

Primary comparison on E031:

- **always assist**: the original E031 assisted arm;
- **confidence route**: assisted when confidence meets the frozen threshold,
  baseline otherwise.

Primary endpoint: success within two attempts.

Report:

- always-assist successes / 421;
- confidence-route successes / 421;
- paired confidence-route minus always-assist delta.

## Primary gate

Treat top-1 softmax confidence as a useful success-improving routing signal only
if all three conditions hold on E031:

1. confidence-route success > always-assist success;
2. exact two-sided McNemar p < 0.05;
3. repository-stratified source-file-clustered bootstrap 95% CI lower bound for
   the paired success delta > 0.

Bootstrap:

- 5,000 replicates;
- resample source files within repository strata;
- RNG seed `39039`.

If the gate fails, E039 stops this confidence feature as a success-improving
first-turn router. Do not change the threshold grid or confidence transform on
E031 and rerun.

## Secondary diagnostics

Report without changing the gate:

- fraction of E031 tasks routed to assistance;
- recommendation correctness among routed-to-assistance tasks;
- recommendation correctness among abstained tasks;
- first-pass success of the confidence-routed policy;
- mean attempts within the two-attempt budget;
- per-repository results;
- function versus method results;
- E031 success for every preregistered threshold, clearly marked as a
  sensitivity curve rather than threshold selection.

Also report confidence distributions for correct versus wrong recommendations,
but do not derive a second threshold from them.

## Scope

E039 tests only whether the decision head's top softmax probability can decide
whether to expose its **first** recommendation.

It does not alter or test:

- E035 ranked post-rejection correction;
- E037 second-generator replication;
- E036 canonical plan-likelihood ranking;
- the decision head architecture;
- the generator prompt;
- the parser;
- the attempt budget.

A negative result would mean that this simple trained-head confidence feature
does not transfer as a useful routing rule, not that the decision ranking itself
lacks value.
