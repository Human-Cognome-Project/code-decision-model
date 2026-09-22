# E021 — Deterministic corrective-turn harness

Ranking accuracy is only an intermediate metric. The project's primary criterion is
whether a small local generator paired with the decision layer requires fewer corrective
turns than the same generator alone.

E021 establishes an exact repair task and paired measurement harness before attaching a
real generator.

## Repair task

The first task deliberately reuses the hardened masked function and same-class method
call corpus.

The generator receives the masked caller, the structurally controlled candidate
definitions, and an instruction to return the complete repaired function.

The assisted condition additionally receives one fallible recommendation from the
decision model. The baseline condition does not.

## Deterministic verifier

The correct repair is already known from AST-derived supervision.

The verifier replaces the marker in the original caller AST with the machine-labelled
target, parses the generator output, and requires AST equivalence apart from source
locations.

Formatting, whitespace, comments, and quote style may vary. Changing another operation,
choosing the wrong target, changing caller identity, leaving the placeholder, or returning
invalid Python fails.

Verifier feedback names only the failure category. It never reveals the correct target.

## Correction turns

The initial generation attempt is not a correction turn.

~~~text
attempts used:      1  2  3
correction turns:   0  1  2
~~~

Success is always reported separately. If either side of a paired experiment fails to
resolve the task within the attempt budget, the harness does not fabricate a
correction-turn delta.

## Paired comparison

Baseline and assisted runs receive fresh generator instances from the same factory.

For a real generator experiment the factory must pin:

- model revision;
- decoding parameters;
- random seed;
- candidate/task ordering;
- attempt budget.

Only the presence of decision-model evidence should differ.

A recommendation is explicitly described as fallible. Tests require that a bad
recommendation can make the assisted condition worse; the harness does not assume the
decision layer helps.

## Scope

This repair task is intentionally close to the decision model's current training domain.
It is a bridge from isolated ranking to correction burden, not a claim of general software
repair.

## Next experiment

E022 should run one compact open code generator against a pinned subset of these repair
tasks.

The report should include first-pass success, success within budget, correction turns for
paired successes, assisted-only/baseline-only resolutions, terminal failure rate, and
results by repository and function-vs-method task.

If the assisted condition reduces corrections here, the next step is machine-generated
mutations with real test/compiler feedback rather than expanding the generator or
decision model first.
