# E030 — Import-resolved cross-file call supervision

Every hard task in the frozen E027 protocol resolves a masked call inside one
file: same-file function calls (E006) and same-class method calls (E015). The
architecture claim is about repository decisions, and OPEN_DIRECTIONS lists
cross-file callable selection as the next machine-verifiable step. E030 adds it
without a language server.

## Label

A top-level function becomes a caller when its body directly calls exactly one
distinct imported name that resolves, by deterministic import resolution, to a
top-level function defined in another file of the same repository:

```text
from package.module import name        # module-level statement in the caller's file
    -> package/module.py or package/module/__init__.py, in this repository
    -> a unique top-level `def name` in that file
```

Resolution rules, all deterministic:

- absolute imports resolve only under explicitly supported roots: the
  repository root and each declared source root (`src` by default, settable
  through `source_roots`). There is no implicit-relative fallback through the
  importing file's ancestors, because Python 3 does not resolve absolute
  imports that way;
- a module path that matches more than one file, across roots or as both
  `name.py` and `name/__init__.py`, is ambiguous and skipped;
- relative imports follow the usual package rules, including `from . import x`
  against `__init__.py`;
- only direct module-level `from ... import ...` statements count;
- an import that resolves to a third-party package, the standard library, a
  missing file, a class, a constant, or a non-unique name is ignored.

The import statement is not part of the caller context, and the alias is
masked as `__CALL_TARGET__`.

## Integrity controls

The E006/E008/E015 controls carry over, plus three new ones:

| Control | Rule |
| --- | --- |
| nested scopes | calls inside nested functions, lambdas, and classes are not attributed to the caller |
| single target | callers with two distinct cross-file targets are skipped |
| shadowing | an alias that matches a same-file top-level function is skipped |
| ambiguity | an absolute import that could name more than one repository file is skipped |
| alias leakage | the example is discarded if the alias survives anywhere in the rendered caller |
| real-name leakage | with `import name as alias`, the example is also discarded if `name` survives |
| call shape | every candidate shares the target's AST call shape and excludes the caller |
| repository pool | candidates come from the whole repository, so the caller's own file is not privileged |
| fixed count | examples that cannot fill the candidate count are skipped |

The task is registered with the E021 repair verifier, the E023 structured-edit
verifier, and the E011 call-site focus transform, so the frozen protocol runs
on it unchanged.

## Census on this repository

`python examples/census_cross_file_calls.py`

| Task | Decisions at 4 candidates |
| --- | ---: |
| hard same-file function calls (E006) | 59 |
| hard same-class method calls (E015) | 4 |
| hard cross-file function calls (E030) | 65 |

Cross-file supervision is at least as dense as same-file supervision here.
Counts are for the commit snapshot: test files import from `cdm`, so tests
added later change them. Most callers in this repository are test functions; a
library repository will have a different mix, which the census reports per
source file.

The E024 call-site predicate never vetoes the labelled target on the new corpus
(encoded as a regression test), but it prunes far more than on the same-file
task:

| Task | Examples with any veto | Mean survivors of 4 | Predicate + uniform |
| --- | ---: | ---: | ---: |
| hard same-file function calls | 3.4% | 3.93 | 25.8% |
| hard cross-file function calls | 46.2% | 2.97 | 44.0% |

Same-file pools share local naming so same-shape candidates usually also share
keyword names; repository-wide pools do not. Any scorer result on this task must
therefore be reported against the predicate-plus-uniform baseline, not raw
chance, and the live loop should apply the predicate before the recommendation
so the two effects are separable.

## What this tests, per the contribution rule

1. **Open question**: does the frozen decision layer reduce corrective burden
   when the target is defined in a different file, where naming and local style
   carry less information than in the same-file tasks?
2. **Deterministic signal**: the same verifiers as E025/E027, with an
   import-resolved label instead of a same-file AST label.
3. **Comparison**: the E027 leave-one-repository-out result on same-file tasks
   under the identical protocol.
4. **Stop condition**: if the assisted arm does not beat baseline on cross-file
   decisions with the same-file-trained scorer, and still does not after the
   scorer is trained on pooled same-file plus cross-file supervision, the
   architecture's repository-level claim is limited to intra-file decisions and
   the direction should stop in favour of retrieval-first designs.

## Not yet covered

- `import package.module` followed by `package.module.name(...)` attribute calls;
- imports inside function bodies, `try` blocks, or `if TYPE_CHECKING` guards;
- names re-exported through `__init__.py` from a deeper module;
- cross-file method calls on imported classes.

Each is a strictly larger resolver over the same integrity controls.
