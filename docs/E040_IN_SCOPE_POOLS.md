# E040 — In-scope candidate pools: the retrieval stage, measured

Every hard task in the frozen protocol shows the decision model four
candidates that the extractor chose to share the target's AST call shape. That
control is what makes the tasks hard rather than trivially name-matchable, but
it also fixes the size of the decision at four, and nothing so far has measured
the size of the decision a local assistant actually faces. OPEN_DIRECTIONS
names this the two-stage path: an independent retrieval or shortlisting stage,
then decision-model reranking, with target recall after retrieval measured
separately from reranking accuracy so a miss cannot hide inside decision
accuracy. E040 is the retrieval stage, made deterministic and measured, with no
model.

## Two pools

For a masked direct call `__CALL_TARGET__(...)` inside a module-level function,
`cdm.scope` builds two candidate pools:

- **scope pool**: the module-level functions defined in the caller's file, the
  caller itself excluded, plus every name imported by a module-level
  `from ... import ...` statement that resolves, under the E030 conservative
  resolver, to a top-level function in another file of the repository, with
  aliases that are shadowed by a local definition excluded. This is what the
  callee could be without editing the imports.
- **repository pool**: every top-level function in the repository other than
  the caller. This is what the callee could be if the assistant may also add an
  import.

Both pools contain repository-defined top-level functions only. Builtins,
classes, names imported from outside the repository, and other module-level
callables are left out, so each pool is a lower bound on what the masked call
could legally name.

A candidate is identified by its rendered text, which is all a scorer sees.
Functions with identical renderings in different files are one candidate, and
sizes count distinct renderings. A task whose target shares its rendering with
another bindable pool member is ambiguous at that level and is not re-posed.

Both pools are functions of the file's source and the repository's files only.
The label is read afterwards. For each pool the census reports its size, how
many members the E024 binding predicate leaves (`CallSiteBindable` over the
same renderings the hard extractors use), and how many share the target's call
shape (the extractor's own notion of a hard negative). It also reports:

- **protocol negatives in scope**: how many of the frozen task's own wrong
  candidates are in the caller's scope pool. When none are, dropping
  out-of-scope names from the frozen task leaves only the target, with no
  model.
- **target in scope independently**: whether the target would be in scope
  without the masked call. A same-file target always is. A cross-file target
  is in scope through its import line, and when no other code in the file
  reads that alias, the import exists only because of the masked call. E030
  deliberately withholds that import from the scorer's context, so a scope
  filter that relies on it reads the answer.
- **target recovery**: whether the labelled target is in each pool and
  bindable. This is a consistency check, not a finding. The extractors label
  from the same symbol collection and resolver, so a miss means a bug, and
  the test suite asserts full recovery on this repository's corpora.

`pool_example` then re-poses any existing task over its bindable pool at either
level, keeping the context, question and truth, so the frozen scorer can be
evaluated on the same decisions at their real size. `candidate_count=None`
gives the pool-complete task; a count gives the target plus that many bindable
negatives, drawn by the extractors' stable-hash convention.

## Census on this repository (four-candidate protocol)

`python examples/census_in_scope_pools.py`

The corpus is this repository's own source, tests included, at this commit:
515 top-level functions, 509 distinct renderings once the caller is excluded.
Adding code changes the numbers, and the script reproduces them.

| Measure | Same-file functions (E006) | Cross-file functions (E030) |
| --- | --- | --- |
| Tasks | 103 | 118 |
| Consistency: target in scope, bindable, in repository | 103, 103, 103 | 118, 118, 118 |
| Protocol negatives in caller scope | 309/309 | 12/354 |
| Scope filter alone resolves the frozen task | 0/103 | 106/118 (89.8%) |
| Target in scope without its own call | 103/103 | 91/118 |
| Scope filter resolves, target in scope independently | 0/103 | 82/118 (69.5%) |
| Scope pool size | mean 18.6, median 18, max 41 | mean 15.7, median 10, max 41 |
| Scope E024-bindable | mean 10.3, median 9, max 20 | mean 4.2, median 2, max 20 |
| Scope, same call shape as target | mean 9.6, median 6, max 20 | mean 2.7, median 1, max 14 |
| Scope solved by predicate alone | 0/103 | 57/118 (48.3%) |
| Scope bindable ≤ 4 | 14/103 (13.6%) | 88/118 (74.6%) |
| Repository E024-bindable | mean 199.3, median 241 | mean 71.2, median 15, max 161 |
| Ambiguous at repository scale | 2/103 | 0/118 |
| Pool-complete tasks, scope level | 103, mean 10.3 candidates | 118, mean 4.2 candidates |
| Pool-complete tasks, repository level | 101, mean 200.1 candidates | 118, mean 71.2 candidates |

Reading:

- **The same-file protocol is a sample of the in-scope decision.** Every
  protocol negative is in the caller's scope, so the frozen task is four
  members of a scope decision that averages ten bindable candidates. Only 14%
  of tasks are within four. Bindability never resolves a same-file task and
  prunes about as far as the extractor's shape matching does. The frozen
  four-candidate result therefore measures same-file ranking at less than half
  its in-scope size.
- **The cross-file protocol is not the in-scope decision.** E030 draws
  negatives from the whole repository, and 342 of its 354 negatives are names
  the caller cannot reach without a new import. A scope filter that reads the
  file's imports resolves 89.8% of the frozen cross-file tasks with no model.
  That filter partly reads the answer: in 27 tasks the target's import is read
  nowhere else in the file, which is the leak E030 removes from the context.
  Counting only targets in scope independently of the masked call, the scope
  filter still resolves 69.5%. Any E030 scorer result is therefore a result on
  a decision that a scope-aware assistant would mostly not face, and it must be
  reported against this baseline as well as the E030 predicate-plus-uniform
  baseline.
- **The real cross-file decisions are small or large, not four.** At scope
  level the decision has two bindable candidates on median and the predicate
  alone resolves 48% of tasks, though for 27 tasks that scope contains the
  target only through the withheld import. When the import does not already
  exist, the assistant faces the repository pool: 15 bindable candidates on
  median and up to 161.
- **Repository scale is a different problem.** Bindability prunes the 509
  distinct repository functions to about 200 for a same-file call. A local
  assistant that may add imports faces a decision one to two orders of
  magnitude larger than the protocol, and the binding predicate is far from
  enough to shortlist it. That is the case for a real retrieval stage in front
  of the scorer. Two same-file targets render identically to another function
  and are not re-posed at this level.

## What this tests, per the contribution rule

1. **Open question**: how large is the decision behind each hard task at the
   scope and repository levels, how far does the deterministic predicate prune
   it, and does the frozen scorer's advantage survive when it must rank the
   real pool rather than four shape-matched candidates?
2. **Deterministic signal**: pool membership and size from the AST and the
   E030 resolver; E024 bindability; distinct renderings; whether the target's
   import is read outside the caller. Target recovery is asserted by the test
   suite as a consistency check.
3. **Comparison**: the four-candidate protocol on the same decisions; the
   scope filter alone on the frozen task; uniform choice over the bindable
   pool as chance at pool scale, which already includes both the scope filter
   and the predicate; the predicate-alone count.
4. **Stop condition**: the measurement half is complete with this PR and the
   census above. The live half, to be preregistered before it runs, is a
   pool-scale run of the frozen E027 scorer on pool-complete `pool_example`
   tasks over the E031 repositories, reported as top-1 accuracy against
   uniform-over-bindable-pool chance, then paired corrective burden as in E031.
   Same-file tasks are run at scope level. Cross-file tasks are run at scope
   level only when the target is in scope independently of the masked call, and
   at repository level otherwise, so no scope-level result rests on the
   withheld import. If scope-level top-1 accuracy does not beat chance by a
   clustered confidence interval, the scorer's four-way result does not
   transfer to the real decision and the next step is a retrieval stage, not
   more ranking. If it does, repository level is the following gate.

## Implementation

`src/cdm/scope.py`:

- `in_scope_pools(root, *, source_roots=("src",))`: one `InScopePool` per
  module-level function, keyed by (file, caller), reusing the E006 symbol
  collection and the E030 import resolver. Each pool records which imported
  members are read outside the caller.
- `RepositoryScope.pool_for`, `repository_pool` and `level_pool`: the pools
  for a task, the caller read from the task context.
- `distinct_by_rendering`, `bindable_mask`, `target_symbol`, and
  `pool_census`, which returns a `PoolCensus`.
- `pool_example` and `pool_examples`: the task re-posed over its bindable
  pool, or None when the target is not bindable, is ambiguous, or the pool
  cannot fill the requested count.

Nothing here trains, scores, or calls a model. `examples/census_in_scope_pools.py`
prints the census for any repository.
