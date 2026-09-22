# E022 — Open generator on the corrective-turn harness

E021 established the deterministic repair task, verifier, and paired measurement
harness. The mock companion under E021 proves the measurement path without a
model download.

E022 is the first **live** open-generator experiment.

## Goal

Measure whether a fallible decision recommendation reduces deterministic
correction turns when a pinned compact open code generator attempts masked call
repair.

## Fixed conditions

Both arms use the same:

- pinned held-out repair examples from the hard masked function/method corpus;
- attempt budget (default 3);
- deterministic verifier from E021;
- generator factory (fresh instance per arm);
- model revision, decoding parameters, and seed.

Only the presence of a fallible decision recommendation differs.

## Generator contract

```text
generate(prompt: str) -> str
```

Implementations satisfy `cdm.generators.RepairGenerator`. The generator returns a
complete Python function (optionally fenced). The harness extracts the code,
verifies AST equivalence against the machine-labelled target, and supplies
category-only feedback on failure.

A recommendation is always described as fallible. The assisted arm is allowed to
do worse than baseline; the harness does not assume benefit.

## Scope for the first live run

- One compact open code model (revision pinned).
- CPU-optional path; import-guarded so default CI does not download weights.
- Held-out subset only; no training or threshold tuning on test labels.
- Report:
  - first-pass success rate
  - success within budget
  - correction turns for paired successes
  - assisted-only / baseline-only resolutions
  - terminal failure rate
  - breakdown by repository and function-vs-method task

## Adapter scaffolding

- `cdm.hf_generator.HFCausalRepairGenerator` — optional Hugging Face causal LM
  adapter implementing `RepairGenerator`. Loads only when constructed without
  injected tokenizer/model; requires `pip install -e ".[hf]"`.
- `examples/run_corrective_turn_hf_smoke.py` — optional single-example smoke
  (downloads weights; not part of default CI).
- Unit tests inject fakes; no network in `pytest`.

Default smoke pin: `Salesforce/codegen-350M-mono` (replace with any pinned
open causal code model when running the real held-out experiment).

## Out of scope for E022

- Expanding the generator or decision head before the measurement exists.
- Soft confidence routing (see E020 negative result).
- Claiming product utility from ranking accuracy alone.

## Follow-on

If the assisted condition reduces corrections on this bridge task, the next step
is machine-generated mutations with real test/compiler feedback rather than
immediately enlarging models.
