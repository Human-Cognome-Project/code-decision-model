# E034 — Closed-vocabulary argument operations

E033 asked the compact generator for one free-form call expression and stopped
at the validity gate: 36/64 outputs parsed, 2/64 were exact, and the failures
were bare symbols, partial signatures, and retained placeholders. E023 showed
the same generator emits a candidate index with perfect reliability, and E032
showed it follows a second recommendation 95% of the time. The difference is
not the difficulty of the decision; it is the entropy of the output surface.

E034 is the successor AGENT.md asks for: a narrow, machine-checkable operation
schema that separates target choice from argument edits, with every token drawn
from a closed vocabulary.

## Output schema

```text
candidate <k>[; <op>]*

keep                 no argument change
swap <i> <j>         exchange positional arguments i and j (1-based)
drop <name>          remove keyword argument <name>
rename <old> <new>   rename keyword argument <old> to <new>
name <i> <param>     turn positional argument i into <param>=...
unname <name>        turn keyword <name>=... into the last positional
```

Indices refer to the call site, keyword names must exist at the call site, and
parameter names come from the candidate signatures in the prompt. No expression
is ever generated; values only move.

## Task construction

The three hard masked-call families supply decisions whose call sites are
already correct, so the operations would always be `keep`. E034 perturbs the
masked call deterministically, in a way that is restorable from visible
information, and keeps the original call as the machine-labelled truth:

| Perturbation | Applied to the call site | Restoring operation |
| --- | --- | --- |
| swap | the last two positionals exchanged | `swap i j` |
| keywordize (opt-in) | the last positional given the target's parameter name | `unname <param>` |
| bogus_keyword | an extra keyword named after a negative candidate's parameter, value copied from an existing argument | `drop <name>` |
| rename_keyword | the last keyword renamed to a negative candidate's parameter | `rename <bogus> <original>` |

`keywordize` is excluded by default: `f(x, 3)` and `f(x, depth=3)` execute
identically, so restoring it is a form edit rather than a repair. The other
three change what the call does (wrong argument order, or a `TypeError`
against the real signature).

One perturbation is chosen per decision by a stable hash. Decisions with more
than one masked call site, starred arguments, or no applicable perturbation are
skipped. Candidates, answer index, and the decision scorer's job are unchanged,
so the E027 recommendation machinery applies as is.

## Verification order

| Check | Failure category |
| --- | --- |
| parses as `candidate <k>` plus operations | `invalid_plan` |
| every operation applies at the call site | `inapplicable_operation` |
| result binds the chosen candidate's signature (E024) | `unbindable_call` |
| spliced caller equals the unperturbed repair | `wrong_target` / `wrong_operations` |

Feedback is category-only. Wrong target and wrong operations are separated, as
in E033, so ranker error and generator error stay distinguishable.

## Model-free baseline

The operation space is small enough to enumerate. `predicate_search` applies
every single operation for every candidate and keeps the plans that bind. Two
quantities matter:

- **solved by predicate alone**: the restoring plan is the only binding plan;
- **one binding plan per candidate**: bindability has reduced the problem to
  target selection, which is exactly the E027 decision.

The second case is where this design is meant to live: the deterministic layer
resolves the arguments and the ranker resolves the target. Any live result must
be reported against this baseline, not against chance.

`python examples/census_argument_ops.py` reports both on a repository.

## What this tests, per the contribution rule

1. **Open question**: can the frozen compact generator emit a correct plan from
   a closed vocabulary, and does the fallible recommendation reduce corrective
   burden when the output is a plan rather than an index?
2. **Deterministic signal**: the four-stage verifier; the unperturbed E021
   repair as truth; E024 bindability on the edited call.
3. **Comparison**: the predicate-search baseline (no model); E027/E031 on the
   same decisions under the index protocol; E033 as the free-form floor.
4. **Stop condition**: a baseline-only validity pilot first, as for E033. If
   plan parse validity does not approach the index protocol's, or exact
   restoration on the known-perturbation set does not beat the predicate-alone
   baseline, closed-vocabulary edits are also beyond this generator and the
   next step is a larger generator, not another schema.

## Predictions

- Parse validity should be far above E033's 56%, because every token is a
  word the prompt has already shown.
- If the generator follows recommendations as in E028 and E032, `wrong_target`
  will track ranker accuracy and the residual will be `wrong_operations`, which
  isolates the generator's edit competence for the first time.
- On decisions where bindability leaves one plan per candidate, assisted
  success should approach E027's, since the task has collapsed to selection.

## Out of scope

E031 and the E032 replication gate remain frozen and exclude this. E029/E032
memory can be composed with this loop later; the first live run is the plain
baseline-only validity pilot.
