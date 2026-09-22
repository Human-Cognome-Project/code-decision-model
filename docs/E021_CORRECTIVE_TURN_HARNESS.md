# E021 — Corrective-turn evaluation harness

The project's primary success criterion is not ranking accuracy. It is whether a small local
code generator paired with the decision layer needs materially fewer correction turns than the
same generator alone.

E021 establishes the measurement contract and the first deterministic repair adapter before a
real generator is attached.

## Generic paired measurement

Each bounded correction episode has three replaceable components:

1. a generator produces one or more candidate artifacts for the current turn;
2. a selector chooses one candidate;
3. a deterministic validator decides whether the selected candidate satisfies the task.

The baseline selector accepts the generator's first candidate. The assisted condition may use
the code decision model over the same generated candidate set.

Baseline and assisted conditions receive fresh generator instances from the same factory. A
real generator experiment must pin model revision, decoding parameters, seed, turn budget, and
validator.

## Correction-turn definition

The initial generate/select/validate round is not a correction turn.

~~~text
attempted turns:   1  2  3
correction turns:  0  1  2
~~~

Task success is reported separately. If one condition exhausts its budget while the other
succeeds, success changes but no artificial correction-turn delta is invented. A paired turn
delta is reported only when both conditions resolve the task.

## Concrete masked-call repair adapter

The first task-specific adapter reuses the hardened masked function and same-class method call
corpus.

A repair prompt contains:

- one caller containing __CALL_TARGET__;
- the same structurally controlled candidate definitions used by the decision benchmark;
- an instruction to return only the complete repaired Python function.

The assisted prompt may additionally include a fallible decision-model recommendation. This
recommendation does not alter the machine-derived verifier.

## Exact deterministic verifier

The target repair is already known from AST-derived supervision.

The verifier:

1. extracts the target symbol from the labeled candidate;
2. replaces __CALL_TARGET__ in the original caller AST;
3. parses the generator output;
4. requires the output to contain exactly one top-level function and nothing else;
5. requires the same caller identity and sync/async form;
6. rejects a remaining placeholder;
7. compares the actual and expected function ASTs without source-location attributes.

Formatting and quote style may vary, but unrelated code edits fail.

Verifier feedback never reveals the correct target. It reports only categories such as invalid
Python, remaining placeholder, wrong target, changed caller, or unrelated edits.

## E021 gate

CPU-only tests require:

- first-pass success to equal zero correction turns;
- failure followed by success to count exactly one correction;
- paired baseline/assisted measurement to keep task success separate from turn delta;
- invalid selector/scorer outputs to fail loudly;
- exact masked-call repairs to pass whether raw or fenced;
- wrong targets and unrelated edits to fail;
- verifier feedback not to reveal the correct candidate;
- extra module-level output to fail.

## Next experiment

E022 attaches one pinned compact open code generator to the fixed held-out masked-call corpus.

The first paired benchmark should report:

- first-pass success;
- success within the attempt budget;
- mean and median attempts;
- terminal failure rate;
- paired correction-turn delta when both conditions succeed;
- success delta when only one condition succeeds;
- per-repository and per-task results.

This first generator benchmark remains intentionally close to the decision model's training
domain. If assistance reduces correction burden here, the next step is machine-generated
mutations with deterministic test, compile, or type-check feedback rather than a larger model.
