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
  callee could legally be without editing the imports.
- **repository pool**: every top-level function in the repository other than
  the caller. This is what the callee could be if the assistant may also add an
  import.

Both are functions of the file's source and the repository's files only. The
label is read afterwards, to ask whether the target is in the pool.

For each pool the census reports its size, how many members the E024 binding
predicate leaves (`CallSiteBindable` over the same renderings the hard
extractors use), how many share the target's call shape (the extractor's own
notion of a hard negative), and whether the labelled target is recovered at all
and is bindable. Recovery must be total, since the extractors label from the
same symbol collection and the same resolver; the test suite asserts it on this
repository's corpora, so a resolver regression would fail the suite rather
than silently shrink recall.

`pool_example` then re-poses any existing task over its bindable pool at either
level, keeping the context, question and truth, so the frozen scorer can be
evaluated on the same decisions at their real size. `candidate_count=None`
gives the pool-complete task; a count gives the target plus that many bindable
negatives, drawn by the extractors' stable-hash convention.

## Census on this repository (four-candidate protocol)

| Family | Tasks | Target in scope / bindable / repository | Scope pool | Scope E024-bindable | Same shape as target | Scope solved by predicate | Bindable ≤ 4 | Repository pool | Repository E024-bindable |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| same-file functions (E006) | 101 | 101 / 101 / 101 | mean 18.6, median 14, max 41 | mean 10.2, median 7, max 20 | mean 9.5, median 6 | 0/101 | 14/101 (14%) | 508 | mean 200, median 241 |
| cross-file functions (E030) | 118 | 118 / 118 / 118 | mean 15.7, median 10, max 41 | mean 4.2, median 2, max 20 | mean 2.7, median 1 | 57/118 (48%) | 88/118 (75%) | 508 | mean 71, median 16 |

Reading:

- **Recall is total.** Every labelled target is in its scope pool, bindable,
  and in the repository pool. The retrieval stage as defined here never loses
  the answer, so any live pool-scale result is purely about ranking.
- **The same-file decision is about two and a half times the protocol.** After
  bindability, a same-file caller still has ten legal callees in scope on
  average, and only 14% of tasks are within the protocol's four. Bindability
  alone never resolves a same-file task, and it leaves about as many members as
  the extractor's shape matching does: the two prune the same way. The frozen
  four-candidate result therefore measures the ranking problem at less than
  half its in-scope size.
- **The cross-file decision is mostly small.** Cross-file callees are rarer in
  scope; bindability leaves two on median, resolves 48% of tasks outright, and
  75% of tasks are within four. Here the protocol is close to the real
  in-scope decision.
- **Repository scale is a different problem.** Bindability prunes the 508
  repository functions to about 200 for a same-file call and to 16 on median
  for a cross-file call. A local assistant that may add imports faces a
  decision one to two orders of magnitude larger than the protocol, and the
  binding predicate is far from enough to shortlist it. That is the case for
  a real retrieval stage in front of the scorer, and it says the scorer's
  pool-scale behaviour, not its four-way behaviour, is what the product needs.

The corpus is this repository's own source, so numbers shift as the code
changes; the census script reproduces them.

## What this tests, per the contribution rule

1. **Open question**: how large is the decision behind each hard task at the
   scope and repository levels, how far does the deterministic predicate prune
   it, and does the frozen scorer's advantage survive when it must rank the
   real pool rather than four shape-matched candidates?
2. **Deterministic signal**: pool membership and size from the AST and the
   E030 resolver; E024 bindability; target recovery, asserted by the test
   suite.
3. **Comparison**: the four-candidate protocol on the same decisions; uniform
   choice over the bindable pool as chance at pool scale; the predicate-alone
   count.
4. **Stop condition**: the measurement half is complete with this PR and the
   census above. The live half is a preregistered pool-scale run of the frozen
   E027 scorer on `pool_example` tasks over the E031 repositories, reported as
   top-1 accuracy at scope scale against uniform-over-bindable-pool chance,
   then paired corrective burden as in E031. If scope-scale top-1 accuracy
   does not beat chance by a clustered confidence interval, the scorer's
   four-way result does not transfer to the real decision and the next step
   is a retrieval stage, not more ranking. If it does, repository-scale is the
   following gate.

## Implementation

`src/cdm/scope.py`:

- `in_scope_pools(root, *, source_roots=("src",))`: one `InScopePool` per
  module-level function, keyed by (file, caller), reusing the E006 symbol
  collection and the E030 import resolver.
- `RepositoryScope.pool_for(example)` / `repository_pool(example)`: the two
  pools for a task, the caller read from the task context.
- `bindable_mask`, `target_symbol`, `pool_census` → `PoolCensus`.
- `pool_example` / `pool_examples`: the task re-posed over its bindable pool.

Nothing here trains, scores, or calls a model. `examples/census_in_scope_pools.py`
prints the table above for any repository.
