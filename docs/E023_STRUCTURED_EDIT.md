# E023 — Structured-edit corrective turns

E022 showed that a 0.5B full-function generator never crossed the deterministic
validity floor, so correction-turn reduction could not be measured.

E023 removes syntax generation from the path.

## Goal

Ask whether fallible repository decision evidence reduces wrong-selection
correction turns when the generator only emits a candidate index and
deterministic code applies the edit.

## Protocol

```text
prompt  -> generator emits "1".."N"
        -> parse index
        -> apply_structured_edit (replace __CALL_TARGET__)
        -> compare to machine-labelled answer_index
```

- Same hard masked function/method corpus and splits as prior experiments.
- Baseline and assisted arms share generator settings; only the fallible
  recommendation differs.
- Feedback names failure category only (`unparseable_selection`,
  `wrong_selection`); it never reveals the correct index.
- Correction turns count regenerations after the first attempt, matching E021.

## Implementation

- `cdm.structured_edit` — parse, apply, verify, paired loop
- `examples/run_structured_edit_mock.py` — deterministic offline measurement path
- Unit tests inject scripted generators; no model download

## Success signal

- Offline mocks: correct recommendation yields non-negative correction-turn delta
  when both arms succeed; unresolved pairs leave delta undefined.
- Live run (later): report first-pass success, success within budget, paired
  correction-turn delta, and failure-category breakdown on held-out examples.

## Out of scope

- Full-function generation (E022 already measured that floor).
- Soft confidence routing (E020 negative).
- Expanding the decision head before this narrower causal question is answered.
