# E041 — Scope-pool reranking preregistration

E040 measured the candidate pool hidden behind the frozen four-candidate
same-file task. On this repository, E024 bindability still left roughly ten
in-scope candidates on average, so the four-way benchmark is only a sampled
decision.

E041 asks the narrowest possible scale question:

> Does the frozen E031 decision scorer still rank the machine-labelled target
> above a predicate-plus-uniform baseline when the same held-out same-file
> function task is expanded from four candidates to its complete E024-bindable
> in-scope pool?

This document freezes the repositories, task family, pool construction, scorer,
primary statistic, bootstrap, and stop rule before any E041 scorer result is
inspected.

E041 is deliberately scorer-only. It does not call the generator, alter the
structured-choice prompt, or introduce the E030 cross-file task. Those would
confound candidate-pool scaling with a new generator surface or a new task
family.

## Frozen repositories

Use the exact four development-independent E031 repositories and revisions:

1. AlphaFold — `c77e5d2a8961d1a353632c462914ff0a32a950f6`
2. Pyodide — `e4d3ae954d01d61a3e90531d63b881f2d33361b4`
3. Optuna — `7d08bfa1824606d7caedb80abfd8558bc63826d7`
4. pytest — `6a9ba0f02f827a54cff6ab4da0dddecd65444ff6`

No repository may be replaced after extraction or scoring.

## Frozen source task family

Start from the exact E031 same-file function extractor only:

- `repository_hard_masked_call_examples`;
- candidate count 4;
- candidate body characters 512;
- extraction seed 0.

The frozen E031 function counts are:

| Repository | Same-file function tasks |
| --- | ---: |
| AlphaFold | 23 |
| Pyodide | 34 |
| Optuna | 79 |
| pytest | 86 |
| **Total** | **222** |

These counts must reproduce before pool expansion.

Methods are excluded because E040 currently defines function pools, not
same-class method pools. Cross-file functions are excluded from the primary
E041 gate so that the only changed factor is candidate-pool size.

## Frozen pool construction

For each repository, build E040 `in_scope_pools` from the pinned source tree.

For each of the 222 frozen same-file function tasks, construct:

`pool_example(example, scope, level="scope", candidate_count=None, body_chars=512)`

This means:

- the caller itself is excluded;
- candidates are repository-defined top-level functions already in the caller's
  deterministic E040 scope;
- duplicate renderings collapse;
- E024 `CallSiteBindable` is applied before neural ranking;
- the labelled target must be present and bindable;
- a task whose target rendering is ambiguous among bindable scope members is
  not re-posed, exactly as E040 defines.

Any target missing from the pool or vetoed by E024 is an integrity failure and
invalidates the run.

Rendering ambiguity is not an integrity failure; it is a deterministic E040
exclusion because the scorer cannot distinguish identical candidate texts.
Report every such exclusion by repository and source file before reporting
model outcomes.

The E041 primary population is all non-ambiguous pool-complete tasks produced
by this rule. Do not impose a model-dependent or outcome-dependent size filter.

Tasks whose bindable pool contains one candidate remain in the population.
Their predicate-plus-uniform expectation is exactly 1 and the scorer cannot
earn positive excess credit on them.

## Frozen scorer

Use the exact E031 leave-one-repository-out scorer protocol:

- encoder: `nomic-ai/CodeRankEmbed`;
- `CodeRankEncoder(max_length=512, normalize_embeddings=False)`;
- `PairwiseMLPScorer(hidden=32)`;
- context focus: `focus_hard_call_context(..., radius_lines=0)`;
- scorer seed 2;
- one training epoch;
- AdamW, lr `1e-3`, weight decay `1e-2`;
- training order seed 20001;
- batch size 32;
- gradient clip 1.0.

For each held-out repository, train on the exact original E031 four-candidate
function-plus-method examples from the other three repositories. Pool-expanded
tasks are never used for training.

Before accepting any E041 pool result, reproduce the full frozen E031 top-1
counts:

| Held-out repository | E031 tasks | Top-1 correct |
| --- | ---: | ---: |
| AlphaFold | 26 | 11 |
| Pyodide | 53 | 36 |
| Optuna | 134 | 87 |
| pytest | 208 | 110 |
| **Total** | **421** | **244** |

Any scorer reproduction drift invalidates E041.

## Primary endpoint

For pool-complete task `i` with `n_i` E024-bindable candidates:

- neural success: `y_i = 1` if the frozen scorer's top candidate is the
  labelled target, else 0;
- predicate-plus-uniform expectation: `u_i = 1 / n_i`;
- excess: `d_i = y_i - u_i`.

Primary reports:

- total neural top-1 successes / tasks;
- expected successes under predicate-plus-uniform:
  `sum_i 1 / n_i`;
- pooled mean excess:
  `mean_i(y_i - 1/n_i)`.

Uniform-over-four is not the baseline. The comparison is always against the
actual bindable pool size of each task.

## Primary uncertainty and gate

Use a repository-stratified source-file-clustered bootstrap over the E041
primary population:

- 5,000 replicates;
- within each repository, resample source files with replacement;
- include all E041 tasks from each sampled source file;
- statistic: pooled mean `y_i - 1/n_i`;
- RNG seed: **41041**.

E041 passes only if both conditions hold:

1. observed pooled neural top-1 successes exceed the summed
   predicate-plus-uniform expectation;
2. the clustered bootstrap 95% CI lower bound for pooled mean excess is > 0.

No secondary metric can rescue a failed primary gate.

Per-repository excess and intervals are descriptive; every repository is not
required to be positive unless separately preregistered later.

## Secondary diagnostics

Report without altering the gate:

- pool-size mean, median, minimum, maximum by repository;
- fraction of tasks with pool size 1, 2–4, 5–8, 9–16, and >16;
- neural top-1 accuracy by those pool-size bins;
- target rank distribution;
- mean reciprocal rank;
- top-3, top-5, and top-10 target recall where the pool is large enough;
- original four-candidate E031 top-1 accuracy on the same held-out same-file
  function tasks;
- deterministic ambiguity exclusions.

The size-binned and rank metrics are descriptive. Do not derive a new cutoff,
shortlist size, or confidence threshold from this population and rerun E041.

## Stop / continuation rule

If E041 fails its primary gate:

- record the negative result;
- stop direct full-scope reranking with this frozen scorer;
- do not train on E041 pool-expanded tasks;
- do not tune the scorer, encoder, pool definition, bindability predicate, or
  candidate-size cutoff on these E031 repositories;
- move to an explicit retrieval/shortlisting stage before neural reranking.

If E041 passes:

- record the result before any follow-up;
- preregister repository-pool scaling separately;
- do not treat the scope result as evidence that hundreds of repository
  candidates can be ranked directly;
- do not jump directly to a pool-complete generator prompt. Any end-to-end
  corrective-burden experiment needs its own bounded output surface and
  preregistration.

## Out of scope

E041 does not test:

- cross-file E030 tasks;
- method pools;
- repository-wide candidate pools;
- retrieval recall;
- generator behavior;
- ranked correction;
- confidence routing;
- any new decision-head architecture.

Its only changed factor relative to the E031 same-file function scorer
evaluation is the number of deterministic, E024-bindable in-scope candidates.
