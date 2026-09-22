# E021 — Deterministic corrective-turn harness

Ranking accuracy is only an intermediate metric. The project's primary criterion is whether a
small generator paired with the decision layer requires fewer corrective turns than the same
generator alone.

E021 adds the first end-to-end harness for measuring that directly.

## Repair task

The initial task deliberately reuses the hardened masked function and same-class method call
corpus.

The generator receives:

- one caller containing the marker __CALL_TARGET__;
- the same structurally controlled candidate definitions used by the decision benchmark;
- an instruction to return the complete repaired Python function.

The assisted condition additionally receives the decision model's fallible recommended
candidate. The baseline condition does not.

## Exact deterministic verifier

The correct repair is already known from the AST-derived supervision.

The verifier:

1. extracts the target symbol from the machine-labeled answer candidate;
2. replaces __CALL_TARGET__ in the original caller AST;
3. parses the generator output;
4. requires the same caller identity;
5. rejects a remaining placeholder;
6. compares ASTs without source-location attributes.

Therefore whitespace, formatting, and quote style may vary, but unrelated code edits fail.

Verifier feedback never reveals the correct candidate. It reports only categories such as:

- invalid Python;
- placeholder still present;
- wrong call target;
- unrelated code changed.

## Corrective turns

A bounded loop performs:

~~~text
generate -> deterministic verify
             |
             +-- success: stop
             |
             +-- failure: generic verifier feedback -> regenerate
~~~

The harness records every prompt, output, and verifier result.

The first generator benchmark should report:

- first-pass success rate;
- success within the attempt budget;
- mean and median attempts;
- terminal failure rate;
- baseline vs decision-assisted paired outcomes;
- results by repository and task type.

## Scope

This first repair task is intentionally close to the decision model's training domain. It is a
bridge from isolated ranking to the actual correction-burden metric, not a claim of general
software repair.

If the decision-assisted condition reduces corrections here, the next step is to move the same
harness to machine-generated mutations and real test/compiler feedback rather than expanding
the generator or decision model first.
