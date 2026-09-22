# E021 companion — deterministic corrective-turn mock

E021 established the deterministic masked-call repair harness. This companion
example exercises the full paired measurement path without downloading a generator
model.

It is deliberately **not** E022. E022 is reserved for the first real open-generator
experiment.

## Goal

Verify that the E021 harness can distinguish a baseline trajectory from an
assisted trajectory when the only difference is the presence of a fallible
decision recommendation.

## Fixed conditions

Both arms use the same:

- repair example;
- attempt budget;
- deterministic E021 verifier;
- fresh generator factory.

Only the recommendation text differs.

## Mock generators

`examples/run_corrective_turn_mock.py` demonstrates two deterministic cases.

### Recommendation-sensitive generator

Without recommendation evidence, it fails the first attempt and succeeds after
deterministic verifier feedback.

When the correct recommendation is present, it succeeds on the first attempt.

Expected paired result:

~~~text
baseline corrections = 1
assisted corrections = 0
correction_turn_delta = 1
~~~

This proves that the harness measures a real paired turn difference rather than
merely completing two loops.

### Stubborn wrong-target generator

Always emits a syntactically valid but incorrect target. Both arms exhaust their
budget and the paired correction-turn delta remains null.

This guards against inventing a turn advantage when neither condition solves the
task.

## Scope

These mocks validate measurement plumbing only. They make no model-performance
claim.

The real E022 experiment attaches a pinned compact open code generator to the same
E021 harness and reports first-pass success, success within budget, paired
correction turns, asymmetric resolutions, terminal failure rate, and repository /
function-vs-method breakdowns.
