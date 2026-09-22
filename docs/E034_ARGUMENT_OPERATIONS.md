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
candidate <k>; <op>

keep                 no argument change
swap <i> <j>         exchange positional arguments i and j (1-based)
drop <name>          remove keyword argument <name>
rename <old> <new>   rename keyword argument <old> to <new>
name <i> <param>     turn positional argument i into <param>=...
unname <name>        turn keyword <name>=... into the last positional
```

Exactly one operation per plan; `keep` is the explicit no-op. A plan with zero
or several operations is `invalid_plan`. This keeps the generator's action space
identical to the enumerable baseline below.

**The vocabulary is closed and checked.** Every identifier operand (`drop`,
`unname`, both `rename` names, the `name` parameter) must belong to the plan
vocabulary: keyword names present at the call site plus the keyword-capable
parameter names of *every* candidate. The vocabulary is listed in the prompt.
An out-of-vocabulary operand is `invalid_plan` before applicability or
bindability is consulted, so a `**kwargs` candidate cannot launder an invented
keyword through the binding predicate. No expression is ever generated; values
only move.

## Task construction

The three hard masked-call families supply decisions whose call sites are
already correct, so the operation would always be `keep`. E034 perturbs the
masked call deterministically and keeps the original call as the
machine-labelled truth:

| Perturbation | Applied to the call site | Restoring operation |
| --- | --- | --- |
| swap | the last two positionals exchanged | `swap i j` |
| bogus_keyword | an extra keyword, name drawn from the spare vocabulary, value copied from an existing argument | `drop <name>` |
| rename_keyword | the last keyword renamed to a spare vocabulary name | `rename <new> <original>` |
| keywordize (opt-in) | the last positional given the target's parameter name | `unname <param>` |

**Label independence.** The spare vocabulary is the union of parameter names
over all candidates minus the keywords already at the call site; the name is
chosen by a hash of the caller, the candidate set, and the seed. The answer
index is read only to fill in the restoring plan's candidate, which is never
shown. So the visible corruption is a function of what the generator sees, and
the ranker's reading of the prompt cannot recover the label from how the call
was damaged. `corruption_is_label_invariant(example)` is the machine check: it
relabels the example to every other answer and requires the corrupted caller to
be byte-identical. The census reports it for every corpus, and the test suite
asserts it on the repository corpora. The control has teeth: `keywordize`
names the *target's* parameter and fails it, which is why it is opt-in and
excluded from `SEMANTIC_PERTURBATIONS`. (Its other defect stands: `f(x, 3)`
and `f(x, depth=3)` execute identically, so restoring it is a form edit.)

A label-free bogus name may happen to be a real parameter of the target, in
which case the corrupted call can still bind it; the truth is the exact
unperturbed call, so `keep` on such a case is `wrong_operations` rather than
`unbindable_call`. Bindability is a gate, not the oracle.

One perturbation is chosen per decision by a label-free hash. Decisions with
more than one masked call site, starred arguments, or no applicable
perturbation are skipped. Candidates, answer index, and the decision scorer's
job are unchanged, so the E027 recommendation machinery applies as is.

## Verification order

| Check | Failure category |
| --- | --- |
| parses as `candidate <k>; <op>` with every operand in the vocabulary | `invalid_plan` |
| the operation applies at the call site | `inapplicable_operation` |
| result binds the chosen candidate's signature (E024) | `unbindable_call` |
| spliced caller equals the unperturbed repair | `wrong_target` / `wrong_operations` |

Feedback is category-only. Wrong target and wrong operations are separated, as
in E033, so ranker error and generator error stay distinguishable.

## Model-free baseline

`plan_space(item)` enumerates candidate x single operation over the vocabulary:
exactly the set of plans the verifier carries past its first two gates. A test
checks this equivalence end to end by feeding every string on a grid of
positions and names (including an out-of-vocabulary one) through the verifier
and comparing admission against membership. `predicate_search` keeps the
binding subset. `predicate_census` reports, per decision:

- **solved by predicate alone**: the restoring plan is the only binding plan;
- **pure selection**: every candidate has exactly one binding plan, so
  bindability has reduced the problem to target selection, which is exactly
  the E027 decision;
- **at most one plan per surviving candidate**: weaker; candidates with zero
  binding plans are excluded, so this is *not* pure selection and is reported
  separately with the mean number of surviving candidates.

Pure selection is where this design is meant to live: the deterministic layer
resolves the arguments and the ranker resolves the target. Any live result must
be reported against this baseline, not against chance.

### Census on this repository (seed 0, 4 candidates)

| Family | Perturbable | Label-invariant | Mean plan space | Mean binding | Mean surviving cand. | Predicate alone | Pure selection | <=1 per survivor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| same-file functions | 34/98 | 34/34 | 37.5 | 4.9 | 3.88/4 | 0/34 | 29/34 (85%) | 31/34 (91%) |
| same-class methods | 4/4 | 4/4 | 12.0 | 12.0 | 4.00/4 | 0/4 | 0/4 | 0/4 |
| cross-file functions | 81/115 | 81/81 | 100.0 | 8.8 | 3.33/4 | 3/81 (4%) | 29/81 (36%) | 33/81 (41%) |

Reading: bindability prunes the plan space by roughly an order of magnitude
but almost never resolves a decision on its own. On the same-file family it
usually leaves exactly one binding plan per candidate; on the cross-file family
it does so for about a third, and there a further fifth of decisions have a
candidate with several binding plans or none. The gap between the last two
columns is the number of decisions the earlier draft of this note would have
over-credited as pure selection. The four method-call decisions all bind every
plan because E024 accepts either the bound or the static reading for receiver
calls; they are too few to matter.

`python examples/census_argument_ops.py` reproduces the table. The corpus is
this repository's own source, including the census script, so the numbers
shift slightly whenever the code changes; treat them as a shape, not a
benchmark.

## What this tests, per the contribution rule

1. **Open question**: can the frozen compact generator emit a correct plan from
   a closed vocabulary, and does the fallible recommendation reduce corrective
   burden when the output is a plan rather than an index?
2. **Deterministic signal**: the four-stage verifier; the unperturbed E021
   repair as truth; E024 bindability on the edited call; the label-invariance
   control on the task generator.
3. **Comparison**: the predicate-search baseline over the identical plan
   space (no model); E027/E031 on the same decisions under the index protocol;
   E033 as the free-form floor.
4. **Stop condition**: a baseline-only validity pilot first, as for E033. If
   plan parse validity does not approach the index protocol's, or exact
   restoration on the known-perturbation set does not beat the predicate-alone
   baseline, closed-vocabulary edits are also beyond this generator and the
   next step is a larger generator, not another schema.

## Predictions

- Parse validity should be far above E033's 56%, because every token is a
  word the prompt has already shown and the vocabulary is listed.
- If the generator follows recommendations as in E028 and E032, `wrong_target`
  will track ranker accuracy and the residual will be `wrong_operations`, which
  isolates the generator's edit competence for the first time.
- On pure-selection decisions, assisted success should approach E027's, since
  the task has collapsed to selection. Report the pure-selection subset
  separately from the rest.

## Out of scope

E031 and the E032 replication gate remain frozen and exclude this. E029/E032
memory can be composed with this loop later; the first live run is the plain
baseline-only validity pilot. Multi-operation plans are a later extension and
must be enumerated by the baseline at the same bound before being allowed to
the generator.
