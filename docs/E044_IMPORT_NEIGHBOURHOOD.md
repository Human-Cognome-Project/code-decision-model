# E044 — Import-neighbourhood pools: a deterministic first stage for cross-file calls

E042 showed that the frozen scorer keeps ranking signal over complete
repository pools, but that ranking hundreds of candidates directly is not a
practical selection stage. E043 tests context-cosine retrieval as the bounded
first stage for E030 cross-file calls. E044 measures a model-free alternative
for the same tasks: the functions defined in the repository files that the
caller's file already imports from.

The question is how often the target's module is already a dependency of the
caller's file for reasons other than the masked call, and how small the
resulting pool is. Nothing here trains, scores, or calls a model.

## The pool

The target's own import is the E030 label, so it must not reach the pool.
`cdm.neighbourhood` reads the caller's file as it would be without that import,
in two variants:

- **alias removed** (primary): every module-level name bound to the target is
  deleted from its import statement, and a statement left with no names is
  dropped. Other names imported from the same module remain.
- **independent** (strict): additionally, an imported name counts only if code
  outside the caller reads it, as in E040's independence measure, and star
  imports do not count. Each remaining module is then in the neighbourhood
  because of the file's other code, not because of the masked caller.

A neighbourhood file is any repository file, other than the caller's own, that
a remaining module-level import resolves to under the unchanged E030
conservative resolver. That covers the module of a `from ... import ...`
statement, a submodule named by one of its names, and the module of an
`import a.b` statement. The pool is every top-level function in those files,
rendered, deduplicated by rendering and pruned by the unchanged E024 binding
predicate exactly as in E040.

By construction, the target is in the pool exactly when another remaining
import resolves to its defining file. A miss therefore means that no other
import in the file, in a form the E030 resolver handles, names the target's
module.

The comparison is the recall of a uniform random subset of the bindable
repository pool with the same size as the neighbourhood pool.

## Census on the pinned E031 repositories

`python examples/census_import_neighbourhoods.py ROOT ... --body-chars 512`

Tasks come from the E030 extractor with the E031/E043 settings: four
candidates, 512-character bodies, seed 0 and the default source roots. The
repositories are at the E031 revisions. They were already used by E031 and
E041 to E043, so this is a descriptive census, not a confirmatory test. No
task was rendering-ambiguous at repository level, and every task had a
module-level name binding its target.

| Repository | Tasks | Alias removed: recall | Independent: recall | Uniform, same size | Bindable pool, median (max) | Pool ≤ 32 with target | Repository bindable, median |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| AlphaFold | 0 | – | – | – | – | – | – |
| Pyodide | 3 | 2 | 2 | 0.0 | 7 (7) | 2 | 848 |
| Optuna | 187 | 127 (67.9%) | 125 (66.8%) | 13.2 | 2 (20) | 127 | 277 |
| pytest | 75 | 64 (85.3%) | 64 (85.3%) | 3.7 | 32 (85) | 32 | 1,121 |
| **Total** | **265** | **193 (72.8%)** | **191 (72.1%)** | **16.9** | **4 (85)** | **161 (60.8%)** | |

"Pool ≤ 32 with target" counts tasks whose alias-removed pool has at most 32
bindable candidates and contains the target. 32 is E043's preregistered
shortlist budget. The column is descriptive and selects nothing.

Reading:

- **The target's module is usually already imported.** Removing only the
  target's name, the neighbourhood contains the target on 72.8% of tasks,
  against 16.9 expected hits (6.4%) for a random pool of the same size. The
  strict variant loses two tasks, so the recall does not rest on names that
  only the masked caller uses.
- **The pools are small where the neighbourhood works.** The median bindable
  pool has four candidates. Every Optuna pool is within 32. pytest files import
  from many modules, so its pools are larger: median 32, maximum 85. Across
  all tasks, 161 of 265 have a pool within E043's budget that contains the
  target.
- **The misses are single-purpose imports of shared utilities.** In every
  miss, no other resolvable import in the file names the target's module. The
  inspected Optuna misses import the target alone, as in
  `from optuna._warnings import optuna_warn`. In Optuna, 16
  of the 60 misses import the same warning helper, and ten more import from one
  multi-objective utility module. A signal about how widely a function is
  imported across the repository might cover these, but E044 does not test one.
- **Two repositories carry the census.** AlphaFold yields no E030 tasks, and
  Pyodide yields three. Optuna contributes 187 of the 265 tasks, so the totals
  mostly describe Optuna.

On this repository at this commit, the same census gives 87 of 119 for both
variants, with a median pool of four. Adding code changes these numbers, and
the script reproduces them.

## Relation to E043

E043 asks whether context-cosine retrieval reaches 75% recall at 32 candidates
on the same tasks. E044 is not a competitor under that rule and does not
change it. The neighbourhood is deterministic, costs no encoding, and misses a
predictable class of targets. It is a candidate component of a first stage,
not a replacement for retrieval over the repository.

## What this tests, per the contribution rule

1. **Open question**: how often does a cross-file call target a module that
   the caller's file already imports for other reasons, and how small is the
   deterministic pool that results?
2. **Deterministic signal**: module-level imports resolved by the E030
   resolver, with the target's name removed; E024 bindability; distinct
   renderings; reads outside the caller for the strict variant.
3. **Comparison**: a uniform random subset of the bindable repository pool of
   the same size; the strict variant against the primary one.
4. **Stop condition**: the measurement is complete with this census. Any use
   of the neighbourhood as a first stage needs its own preregistration, fixed
   before any scoring. The natural one fills a fixed budget from the
   neighbourhood first and a frozen retriever second, and compares recall at
   that budget with the retriever alone on the E043 population. If the
   combination does not beat the retriever alone by a clustered confidence
   interval, the neighbourhood stage should be dropped.

It does not establish reranking accuracy, end-to-end success, or corrective
burden. Nothing here selects a shortlist size.

## Implementation

`src/cdm/neighbourhood.py`:

- `import_neighbourhoods(root, *, source_roots=("src",))` parses every
  repository file once, with the E006/E030 symbol collection.
- `RepositoryNeighbourhoods.target_aliases`, `neighbourhood_files` and
  `neighbourhood_pool` give the names removed, the neighbourhood files and
  their functions for a task, in either variant.
- `neighbourhood_census` returns a `NeighbourhoodCensus` per task.

`examples/census_import_neighbourhoods.py` prints the census for one or more
repositories.
