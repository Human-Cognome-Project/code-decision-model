# E045 — Frozen reranking after CodeRank retrieval result

E045 tested whether the unchanged E031 leave-one-repository-out
`PairwiseMLPScorer(hidden=32)` adds selection value after the exact E043
CodeRank top-32 retrieval stage.

No E030 cross-file task was used for training. Retrieval misses remained
end-to-end failures.

## Population and continuity

The exact E043 population reproduced:

- AlphaFold: 0 tasks;
- Pyodide: 3;
- Optuna: 187;
- pytest: 75;
- total: 265.

There were no rendering-ambiguity exclusions.

All E031 held-out scorer guards reproduced exactly:

- AlphaFold: 11/26;
- Pyodide: 36/53;
- Optuna: 87/134;
- pytest: 110/208.

The E043 retrieval guards also reproduced exactly:

- CodeRank rank-1 target: 122/265;
- target in top 32: 224/265.

## Preregistered primary result

| Metric | CodeRank rank-1 baseline | Frozen E031 reranker |
| --- | ---: | ---: |
| End-to-end top-1 | 122/265 (46.04%) | 123/265 (46.42%) |
| Paired delta |  | +0.38 pp |
| Exact McNemar p |  | 1.0 |
| Clustered 95% CI, paired delta |  | -8.01 to +8.05 pp |

The preregistered gate required all three:

1. more than 122 reranked successes;
2. exact McNemar p < 0.05;
3. clustered 95% CI lower bound > 0.

Only the first condition passed. **E045 therefore fails.**

## Transition structure

The null result is not caused by the reranker doing nothing:

- 33 tasks that CodeRank ranked 2–32 were rescued to rank 1;
- 32 CodeRank rank-1 hits were spoiled by reranking.

Those nearly exact counterflows leave only one net additional success.

Conditional on the target being retrieved, reranker top-1 accuracy was
123/224 (54.91%).

Per repository:

| Repository | CodeRank rank-1 | Reranked top-1 | Delta |
| --- | ---: | ---: | ---: |
| Pyodide | 1/3 | 1/3 | 0 |
| Optuna | 90/187 | 90/187 | 0 |
| pytest | 31/75 | 32/75 | +1 |

AlphaFold contributes no E030 tasks.

## Interpretation

The frozen same-file-trained E031 decision head does not add reliable
cross-file selection value after CodeRank retrieval. It contains useful
cross-file signal—33 retrieval errors are corrected—but that signal is not
calibrated strongly enough to displace the retriever safely, and 32 correct
retrieval winners are lost.

This closes the exact CodeRank -> frozen E031 PairwiseMLP path on this
population. Do not tune the E031 head, shortlist size, or E030 task selection
against this result.

The next main-line question returns to the first stage: whether a
machine-checkable repository dependency signal can improve the fixed CodeRank
shortlist before any new learned reranker is considered.

## Provenance

- preregistration: `docs/E045_RETRIEVED_RERANKING_PREREG.md`
- workflow run: `35969908831`
- live commit: `95a03f09680dd608a21e49074558b35629be7e75`
- aggregate artifact: `10796855308`
- aggregate digest:
  `sha256:8d63f5bf51b64e6f253ec1aef1caaaf2e6800421d12ccedd235365bb95224390`
- bootstrap replicates: 5,000
- bootstrap seed: 45045
