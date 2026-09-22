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

## Live pilot result

Pinned generator: `Qwen/Qwen2.5-Coder-0.5B-Instruct` at revision
`ea3f2471cf1b1f0db85067f1ef93848e38e88c25`.

The same 12 held-out pilot examples used for E022 were evaluated with a maximum
of two selection attempts per arm.

| Metric | Baseline | Assisted |
| --- | ---: | ---: |
| First-pass success | 2/12 (16.7%) | 7/12 (58.3%) |
| Success within budget | 5/12 (41.7%) | 8/12 (66.7%) |
| Terminal failures | 7/12 | 4/12 |
| Mean attempts, all tasks | 1.83 | 1.42 |

Paired outcomes:

- both succeed: 4
- assisted only: 4
- baseline only: 1
- neither succeeds: 3
- among the four paired successes, assisted saved 0.5 correction turns on average
- assisted used fewer corrections on 2/4 paired successes, the same on 2/4, and
  more on 0/4

The decision recommendation was correct on 7/12 pilot tasks (58.3%).

This is the first positive end-to-end signal on the project's corrective-burden
criterion, but the sample is too small for a general claim. The next requirement
is a larger confirmatory held-out run with the same pinned model, split logic,
decision intervention, and strict structured-output parser.

## Out of scope

- Full-function generation (E022 already measured that floor).
- Soft confidence routing (E020 negative).
- Expanding the decision head before this narrower causal question is answered.
