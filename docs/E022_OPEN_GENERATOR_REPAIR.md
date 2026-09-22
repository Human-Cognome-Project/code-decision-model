# E022 — Open generator on the corrective-turn harness

E021 established an exact repair task and paired measurement harness. E022 is
the first experiment that attaches a generator.

## Goal

Measure whether a decision recommendation reduces deterministic correction turns
when a compact open (or mock) generator attempts masked call repair.

## Fixed conditions

Both arms use the same:

- pinned repair examples from the hard masked function/method corpus;
- attempt budget (default 3);
- deterministic verifier from E021;
- generator factory (fresh instance per arm).

Only the presence of a fallible decision recommendation differs.

## Generator contract

```text
generate(prompt: str) -> str
```

The generator must return a complete Python function (optionally fenced). The
harness extracts the code, verifies AST equivalence against the machine-labelled
target, and supplies category-only feedback on failure.

A recommendation is always described as fallible. The assisted arm is allowed to
do worse than baseline; the harness does not assume benefit.

See `cdm.generators.RepairGenerator` for the typed protocol.

## Mock path (this PR)

`examples/run_corrective_turn_mock.py` exercises the full paired loop with two
deterministic mock generators:

1. **recommendation_follower** — uses a stated recommendation on the first
   attempt when present; otherwise fails once and recovers from verifier
   feedback. A correct recommendation yields `correction_turn_delta >= 1`. A
   wrong recommendation is allowed to harm the assisted arm.
2. **stubborn_wrong** — always emits a wrong but valid candidate. Both arms
   fail within budget; no fabricated delta.

These mocks prove the measurement path without downloading a model.

## Real open-generator path (next)

Replace the mock factory with a pinned open code model (revision, decoding
parameters, seed fixed). Report on a held-out subset:

- first-pass success rate
- success within budget
- correction turns for paired successes
- assisted-only / baseline-only resolutions
- terminal failure rate
- breakdown by repository and function-vs-method task

If the assisted condition reduces corrections on this bridge task, the following
step is machine-generated mutations with real test/compiler feedback rather than
immediately enlarging the generator or decision head.

## Success signal for the mock

- Paired runs complete without exception.
- Correct recommendation: assisted first-pass success; baseline needs a
  correction; `correction_turn_delta >= 1`.
- Wrong recommendation: assisted may use more attempts than the good case.
- Stubborn mock produces no success on either arm and a null correction delta.
- No target identity is leaked in verifier feedback.
