# E020 — Selective routing with Potion and CodeRank

E017 established a large efficiency gap between the 16M static Potion encoder and
CodeRankEmbed, but also a substantial accuracy gap when either encoder is used as the final
decision representation.

E020 tested whether that gap could be exploited by routing only uncertain Potion decisions to
CodeRank.

## Fixed corpus

The experiment reused the pinned combined function + same-class method corpus:

- 400 total decisions;
- 277 train / 60 validation / 63 test;
- four candidates per decision;
- source-file-disjoint, repository-stratified splits;
- radius-0 call-site context;
- four pinned post-2024 repositories.

The CodeRank MLP seed was selected by **validation NLL only**. Potion routing thresholds were
also selected on validation only. Test labels were not used for model or threshold selection.

## Baselines

| System | Validation | Test |
| --- | ---: | ---: |
| Random | 25.0% expected | 25.0% expected |
| Potion cosine | 63.3% | 39.7% |
| CodeRank + MLP | 65.0% | 60.3% |

The CodeRank test estimate remains uncertain because there are only 63 held-out examples, but
it substantially outperformed Potion on the same split.

## Potion confidence looked useful on validation

Using the margin between Potion's highest and second-highest cosine scores:

| Potion coverage | Validation selective accuracy |
| ---: | ---: |
| 10% | 100.0% |
| 25% | 86.7% |
| 50% | 83.3% |
| 75% | 73.3% |
| 100% | 63.3% |

This initially appears ideal for selective routing.

It did **not** generalize.

The validation-selected threshold that preserved CodeRank's 65.0% validation accuracy accepted
98.3% of decisions directly from Potion and escalated only 1.7%. On test it accepted 98.4% from
Potion and achieved only **39.7%**, effectively collapsing to the Potion baseline.

Allowing validation tolerances of 2, 5, or 10 percentage points selected Potion for every
decision and produced the same 39.7% test result.

## Runtime evidence

On the GitHub Actions CPU runner:

- Potion context encoding: about 0.000358 seconds/query;
- CodeRank context encoding: about 0.228 seconds/query;
- Potion full-corpus pre-encoding: about 0.365 seconds;
- CodeRank full-corpus pre-encoding: about 310 seconds.

The speed gap is real and very large. The tested confidence signal is not reliable enough to
exploit it as a router.

## Conclusion

**Do not use raw Potion cosine margin as a production escalation signal.**

The failure is informative:

1. a cheap model can appear well calibrated on a small validation split while failing sharply
   on held-out source groups;
2. routing must be evaluated across source/repository boundaries, not ordinary random examples;
3. the extreme efficiency of Potion does not compensate for an unreliable confidence surface.

Potion remains useful as:

- an extreme-efficiency representation baseline;
- a possible large-pool retrieval component to test separately;
- a reference point for future compact encoders.

Further threshold tuning on this 60-example validation set is low-value. A routing model should
only be revisited with substantially more source groups or a stronger out-of-domain calibration
design.

The next priority returns to the project's primary criterion: whether a small generator paired
with the decision layer requires fewer deterministic correction turns than the generator alone.
