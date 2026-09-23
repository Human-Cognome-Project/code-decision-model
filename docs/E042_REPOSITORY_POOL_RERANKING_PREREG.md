# E042 — Repository-pool reranking preregistration

E041 showed that the frozen E031 scorer retains substantial ranking signal when
the four-candidate same-file function task is expanded to the complete
E024-bindable in-scope pool. E042 asks the next scale question without changing
the task family, repositories, scorer, or supervision:

> Does the same frozen scorer still rank the machine-labelled target above a
> predicate-plus-uniform baseline when each held-out same-file function task is
> expanded to its complete E024-bindable repository pool?

This document freezes the population construction, scorer, continuity guards,
primary endpoint, uncertainty, and stop rule before any E042 repository-pool
score is inspected.

E042 is scorer-only. It does not call a generator, introduce retrieval, train
on pool-expanded examples, or alter the decision head.

## Frozen repositories and source tasks

Use the exact E031 repositories and revisions:

1. AlphaFold — `c77e5d2a8961d1a353632c462914ff0a32a950f6`
2. Pyodide — `e4d3ae954d01d61a3e90531d63b881f2d33361b4`
3. Optuna — `7d08bfa1824606d7caedb80abfd8558bc63826d7`
4. pytest — `6a9ba0f02f827a54cff6ab4da0dddecd65444ff6`

Start from the exact E031 same-file function extractor:

- `repository_hard_masked_call_examples`;
- candidate count 4;
- candidate body characters 512;
- extraction seed 0.

Frozen source-task counts:

| Repository | Function tasks |
| --- | ---: |
| AlphaFold | 23 |
| Pyodide | 34 |
| Optuna | 79 |
| pytest | 86 |
| **Total** | **222** |

These counts must reproduce before any pool scoring.

Methods and E030 cross-file tasks remain out of scope. E042 changes only the
candidate pool around the same function decisions already used in E041.

## Frozen repository-pool construction

Build E040 `in_scope_pools` on each pinned repository, then re-pose each
source function task with:

`pool_example(example, pools, level="repository", candidate_count=None, body_chars=512)`

The repository pool is therefore:

- every distinct top-level function rendering in the repository other than the
  caller;
- pruned by the frozen E024 `CallSiteBindable` predicate;
- rendered with the same 512-character body limit as E031/E041.

Integrity requirements:

- the machine-labelled target must be present in the repository pool;
- the target must survive E024;
- target rendering ambiguity is handled exactly as E040: an ambiguous task is
  deterministically excluded before model creation or scoring;
- every exclusion is reported by repository and source file.

Target absence or E024 veto is an integrity failure that invalidates the run.
Rendering ambiguity is a deterministic E040 exclusion, not a model failure.

Do not impose a candidate-count cutoff. The primary population is every
non-ambiguous pool-complete task, regardless of repository-pool size.

## Frozen scorer

Use the exact E031 leave-one-repository-out scorer:

- encoder: `nomic-ai/CodeRankEmbed`;
- `CodeRankEncoder(max_length=512, normalize_embeddings=False)`;
- `PairwiseMLPScorer(hidden=32)`;
- context focus radius 0;
- scorer seed 2;
- one epoch;
- AdamW, lr `1e-3`, weight decay `1e-2`;
- training-order seed 20001;
- batch size 32;
- gradient clip 1.0.

Training remains exclusively on the original four-candidate E031
function-plus-method examples from the other three repositories. Neither E041
nor E042 pool-expanded examples enter training.

## Continuity guards

Before accepting any E042 result, each fold must reproduce the original E031
full-test scorer counts:

| Held-out repository | Top-1 correct / E031 tasks |
| --- | ---: |
| AlphaFold | 11/26 |
| Pyodide | 36/53 |
| Optuna | 87/134 |
| pytest | 110/208 |
| **Total** | **244/421** |

The same trained scorer must then reproduce the E041 complete-scope top-1 counts
on the non-ambiguous E041 function population:

| Held-out repository | E041 scope top-1 |
| --- | ---: |
| AlphaFold | 7/23 |
| Pyodide | 19/34 |
| Optuna | 26/79 |
| pytest | 30/86 |
| **Total** | **82/222** |

E041 had zero ambiguity exclusions. Any E031 or E041 guard drift invalidates
E042 before repository-pool outcomes are interpreted.

The E042 repository population itself must also be frozen and integrity-checked
before the encoder/scorer is initialized.

## Primary endpoint

For repository-pool task `i` with `n_i` E024-bindable candidates:

- `y_i = 1` if the frozen scorer ranks the target first, else 0;
- `u_i = 1 / n_i`;
- `d_i = y_i - u_i`.

Report:

- neural top-1 successes / primary tasks;
- summed predicate-plus-uniform expected successes `sum_i 1/n_i`;
- pooled mean excess `mean_i(d_i)`.

The four-candidate E031 accuracy and E041 scope-pool accuracy are continuity
comparators, not the E042 baseline. The primary baseline is always uniform over
the actual E024-bindable repository pool.

## Primary uncertainty and gate

Use a repository-stratified source-file-clustered bootstrap:

- 5,000 replicates;
- resample source files with replacement within held-out-repository strata;
- include all E042 primary tasks from sampled source files;
- statistic: pooled mean `y_i - 1/n_i`;
- RNG seed: **42042**.

E042 passes only if both conditions hold:

1. observed neural top-1 successes exceed summed predicate-plus-uniform expected
   successes;
2. the clustered bootstrap 95% CI lower bound for pooled mean excess is > 0.

No secondary metric rescues a failed gate.

## Secondary diagnostics

Report without changing the primary gate:

- deterministic ambiguity exclusions and retained-population coverage;
- repository-pool size mean, median, minimum, and maximum;
- pool-size bins fixed in advance:
  - 2–4;
  - 5–16;
  - 17–64;
  - 65–256;
  - >256;
- neural top-1 and uniform expected successes within each bin;
- target-rank histogram;
- mean reciprocal rank;
- top-3, top-5, top-10, top-20, and top-50 target recall where the pool is
  large enough;
- per-repository neural successes, expected successes, and mean excess;
- E031 four-candidate function accuracy and E041 scope-pool accuracy for the
  same held-out folds.

These diagnostics may motivate a future retrieval cutoff but may not be used to
change E042 after results are seen.

## Stop / continuation rule

If E042 fails:

- record the negative result;
- stop direct full-repository reranking with this frozen scorer;
- do not tune the scorer, encoder, repository-pool definition, E024 predicate,
  or candidate-size cutoff on these repositories;
- move to an explicit deterministic/retrieval shortlist stage, whose target
  recall and reranking accuracy must be measured separately.

If E042 passes:

- record the result before any follow-up;
- treat repository-wide direct ranking signal as demonstrated for this frozen
  task/scorer, not as proof of practical latency or generator usability;
- next measure the cost/quality tradeoff of retrieval or a bounded shortlist
  before any end-to-end generator experiment;
- do not expose a variable hundreds-way repository index prompt to the generator
  without a separate output-surface preregistration.

## Out of scope

E042 does not test:

- cross-file E030 tasks;
- method pools;
- generator behavior;
- retrieval quality or latency;
- new scorer training;
- confidence routing;
- ranked correction;
- free-form edit generation.

Its only experimental change from E041 is scope-level pool → repository-level
pool.
