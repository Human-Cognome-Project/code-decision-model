# E046 — Label-free import-neighbourhood priority retrieval

## Status

Preregistered before any E046 hybrid outcome is generated or inspected.

E045 stopped the exact CodeRank top-32 -> frozen E031 PairwiseMLP path. E044
showed that repository import neighbourhoods carry strong deterministic signal,
but its primary census deliberately removed the hidden target alias and was a
measurement construct rather than a deployable inference rule.

E046 tests a label-free version of that idea.

## Frozen population

Use the exact E043/E045 cross-file population and repository revisions:

- AlphaFold: 0 tasks;
- Pyodide: 3;
- Optuna: 187;
- pytest: 75;
- total: 265 retained tasks;
- exact E030 extractor settings;
- exact E024-bindable repository pools;
- distinct 512-character candidate renderings;
- exact focused masked-caller context.

Any extraction, target-presence, bindability, ambiguity, or E043 CodeRank
continuity drift invalidates the run.

## Frozen CodeRank baseline

Reproduce E043 exactly:

- `CodeRankEncoder(max_length=512, normalize_embeddings=False)`;
- context role for the masked caller;
- candidate role for each independently cached candidate;
- cosine similarity;
- stable original-order tie break;
- fixed shortlist size 32.

Continuity guards:

- CodeRank rank-1 target count: 122/265;
- CodeRank top-32 target count: 224/265;
- recall@32: 84.53%.

No PairwiseMLP or generator is used.

## Label-free deterministic neighbourhood

For each task, inspect the caller's repository file without consulting
`answer_index`, the labelled candidate, target name, or target import alias.

Build an **independent import neighbourhood** as follows:

1. parse module-level imports;
2. compute names read by module-level code other than imports and the masked
   caller definition, using the same `_names_read_outside` rule as E040/E044;
3. retain only explicit imported names whose locally bound name is read outside
   the masked caller;
4. exclude star imports because their used bindings cannot be attributed
   conservatively;
5. resolve retained modules/submodules with the unchanged conservative E030
   resolver;
6. collect every top-level function from those resolved repository files;
7. apply the unchanged E024 bindability predicate;
8. deduplicate by the same 512-character rendering used by E043.

This rule never asks which import or candidate is the hidden target. If the
target module enters the neighbourhood, it does so because code outside the
masked caller independently establishes that dependency.

## Hybrid ranking

Use the already-computed frozen CodeRank score for every repository candidate.

Sort candidates by:

1. independent-neighbourhood membership first;
2. descending CodeRank cosine within each membership group;
3. original repository-candidate order for exact score ties.

Take the first **32** candidates, or the whole pool when smaller.

Equivalently, the deterministic neighbourhood is a binary priority bit and
CodeRank remains the only learned ranking signal.

No score weight, threshold, neighbourhood size cap, or shortlist size is tuned.

## Primary comparison

The primary endpoint is paired target recall at the fixed 32-candidate budget.

For each task:

- `baseline_i = 1` if the target appears in E043 CodeRank top 32;
- `hybrid_i = 1` if the target appears in E046 hybrid top 32;
- paired delta = `hybrid_i - baseline_i`.

The frozen baseline is **224/265** hits.

Primary statistics:

- exact McNemar test;
- repository-stratified source-file-clustered bootstrap of paired recall delta;
- 5,000 bootstrap replicates;
- seed **46046**.

E046 passes only if all three are true:

1. hybrid recall@32 exceeds 224/265;
2. exact McNemar p < 0.05;
3. clustered 95% CI lower bound for paired recall delta > 0.

## Secondary diagnostics

Report without changing the gate:

- baseline misses rescued by neighbourhood priority;
- baseline top-32 hits displaced by neighbourhood priority;
- neighbourhood-present task count;
- neighbourhood bindable-pool size distribution;
- hybrid target rank distribution;
- hybrid rank-1 accuracy;
- MRR;
- per-repository results;
- results split by neighbourhood size <=32 and >32;
- comparison with E044's already-recorded target-deleted census, clearly marked
  as descriptive and not a gate.

## Stop / continuation

- **Pass:** the first stage becomes CodeRank plus deterministic dependency
  priority. Before another learned reranker, preregister a selection experiment
  that preserves this fixed retrieval stage.
- **Fail:** drop import-neighbourhood priority as a repository-retrieval
  mechanism on this population. Do not tune weights, thresholds, shortlist
  size, or import rules after seeing the result. Move to a materially different
  machine-checkable signal or representation.

## Out of scope

E046 does not:

- use the hidden target alias to construct the neighbourhood;
- use E044's target-deletion rule operationally;
- train or fine-tune an encoder;
- train a new decision head;
- use the frozen E031 PairwiseMLP;
- change the 32-candidate budget;
- call a generator;
- claim fresh-repository confirmation.
