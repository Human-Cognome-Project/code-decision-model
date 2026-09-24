# E045 — Frozen reranking after CodeRank retrieval

## Status

Preregistered before any E045 reranking outcome is generated or inspected.

E043 passed its fixed retrieval viability rule only for CodeRank. E045 executes
the continuation written into the E043 preregistration: use the frozen CodeRank
retriever as a bounded first stage and test the already-frozen E031 decision
scorer on its shortlist.

This is still an exploratory mechanism experiment on repositories already used
by E031/E041–E044. It is not a fresh generalization claim.

## Frozen population

Use the exact E043 E030 extraction and repository-pool rules:

- pinned E031 repository revisions;
- `repository_hard_masked_cross_file_call_examples(..., candidate_count=4,
  candidate_body_chars=512, seed=0)`;
- focused caller query from `focus_hard_call_context(..., radius_lines=0)`;
- complete E024-bindable repository candidate pool;
- distinct 512-character renderings;
- deterministic target-rendering ambiguities excluded exactly as E043.

Expected retained population from E043:

- AlphaFold: 0;
- Pyodide: 3;
- Optuna: 187;
- pytest: 75;
- total: 265.

Any extraction-count, target-presence, bindability, or ambiguity drift
invalidates the run.

## Frozen retrieval stage

Reproduce E043 CodeRank retrieval exactly:

- `CodeRankEncoder(max_length=512, normalize_embeddings=False)`;
- context encoded with role `context`;
- candidates encoded independently with role `candidate`;
- descending cosine similarity;
- stable candidate-order tie breaking;
- no import text, target alias/name, path hint, scorer output, or E041/E042
  rank in the retrieval query;
- fixed shortlist size **32**, or the complete pool when it has fewer than 32
  candidates.

The E043 retrieval results are continuity guards:

- rank-1 target count: **122/265**;
- target in top 32: **224/265**;
- recall@32: **84.53%**.

A retrieval miss remains an E045 failure. The target is never injected into the
shortlist.

E044 import-neighbourhood information is not used in E045.

## Frozen decision scorer

For each held-out repository, reproduce the exact E031 leave-one-repository-out
scorer before evaluating E045:

- training population: exact E031 same-file function and method tasks from the
  other three repositories;
- exact E031 focused context transform;
- `nomic-ai/CodeRankEmbed`;
- `PairwiseMLPScorer(hidden=32)`;
- E031 optimizer, seed, order, batch size, and one-epoch training protocol;
- no E030 cross-file example in training;
- no pool-expanded or retrieval-derived training example.

The E031 held-out top-1 continuity guards must reproduce exactly:

- AlphaFold: 11/26;
- Pyodide: 36/53;
- Optuna: 87/134;
- pytest: 110/208.

Failure of any guard invalidates the corresponding run.

## Reranking surface

For each E043 task:

1. construct the exact CodeRank shortlist;
2. if the target is absent, record pipeline failure and do not alter the list;
3. if the target is present, re-pose the E030 decision over the retrieved
   candidates in retrieval order;
4. give the frozen PairwiseMLP the exact focused E030 context, the unchanged
   E030 question, and independently encoded shortlisted candidates;
5. take the highest PairwiseMLP score, with stable shortlist order for ties.

No generator is used.

## Primary comparison

The primary endpoint is end-to-end top-1 selection on all 265 E043 tasks.

For task `i`:

- `baseline_i = 1` when raw CodeRank retrieval ranks the target first;
- `rerank_i = 1` when the target is in the top-32 shortlist and the frozen
  PairwiseMLP ranks it first within that shortlist;
- paired delta = `rerank_i - baseline_i`.

The frozen baseline is CodeRank's E043 rank-1 result: **122/265**.

A retrieval miss is `rerank_i = 0`, so retrieval recall remains an explicit
ceiling rather than disappearing from the decision metric.

## Statistics and gate

Primary uncertainty:

- exact McNemar test on paired baseline/reranked outcomes;
- repository-stratified source-file-clustered bootstrap of mean paired delta;
- 5,000 bootstrap replicates;
- seed **45045**.

E045 passes only if all three are true:

1. reranked top-1 successes > 122;
2. exact McNemar p < 0.05;
3. clustered 95% CI lower bound for the paired success-rate delta > 0.

This tests whether the frozen decision head adds selection value beyond the
retriever's own nearest-neighbour ordering.

## Secondary diagnostics

Report without changing the gate:

- conditional reranker accuracy on the 224 E043 retrieval hits;
- retrieval hits rescued from CodeRank ranks 2–32;
- CodeRank rank-1 hits spoiled by reranking;
- transition table baseline correct/incorrect vs reranker correct/incorrect;
- reranker target-rank distribution within the shortlist;
- per-repository results;
- shortlist-size distribution;
- retrieval+uniform expected top-1 success,
  `1 / shortlist_size` only when the target is present;
- scorer runtime after cached candidate embeddings.

## Continuation

- **Pass:** separately preregister an end-to-end bounded pipeline experiment
  before involving a generator or corrective-turn claim.
- **Fail:** do not tune the frozen PairwiseMLP or shortlist on this population.
  Stop this exact CodeRank→E031-reranker path and test a materially different
  first-stage construction or representation. E044's deterministic
  import-neighbourhood hybrid is one already-measured candidate, but would need
  its own preregistration.

## Out of scope

E045 does not:

- retrain or fine-tune CodeRank;
- train the PairwiseMLP on E030 or retrieved candidates;
- use Potion;
- use E044 import neighbourhoods;
- tune shortlist size;
- call a generator;
- measure corrective burden;
- make a new confirmatory generalization claim.
