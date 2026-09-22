# E033 — Call-expression validity pilot result

E033 asked whether the pinned compact Qwen generator could move one step beyond candidate-index selection and emit an actual Python call expression that deterministic code could splice into the masked caller.

Before any paired decision-assisted experiment, a baseline-only first-pass validity pilot measured the generation floor.

## Provenance

- workflow: `e033-call-intent-validity-pilot`
- run: `35794728576`
- branch: `analysis/e033-call-intent-validity-pilot`
- head SHA: `d0f769a04d4149ce89fc06e4c4073409d435c863`
- aggregate artifact: `e033-validity-pilot`
- artifact digest: `sha256:331a03ba8a0eea0f97cc3f4bd59593b7200b8e545caeecb3c7cb0cf3b0761bff`
- generator: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- generator revision: `ea3f2471cf1b1f0db85067f1ef93848e38e88c25`
- sample: 64 tasks, selected outcome-blind by stable hash with repo × family quotas and stable global fill

The pilot was baseline-only: no decision recommendation and no corrective turn.

## Overall result

| Stage | Count | Rate |
| --- | ---: | ---: |
| Output parses as one call expression | 36/64 | 56.3% |
| Callee resolves uniquely to a candidate and call is bindable | 23/64 | 35.9% |
| Exact machine-labelled repair | 2/64 | 3.1% |

Mean generation time was 3.58 seconds per task on the CPU Actions runner.

Verifier reasons:

- `invalid_call_expression`: 28
- `unknown_target`: 12
- `ambiguous_target`: 1
- `wrong_target`: 17
- `wrong_arguments`: 4
- `ok`: 2

## By task family

| Family | n | Parse-valid | Bindable-valid | Exact |
| --- | ---: | ---: | ---: | ---: |
| same-file function | 19 | 10 | 6 | 2 |
| same-class method | 26 | 13 | 8 | 0 |
| cross-file function | 19 | 13 | 9 | 0 |

No family crossed a useful exact-repair floor. Cross-file calls were somewhat more likely to produce a structurally valid call than same-file functions, but none of the 19 cross-file outputs matched the machine-labelled repair.

## Nature of invalid outputs

The parse failures are not mostly superficial formatting mistakes. Representative outputs include:

- bare symbols such as `_candidate_1`, `check_db_path`, and `setup_proxy_auth`;
- partial function signatures rather than calls;
- outputs that retain `__CALL_TARGET__`;
- full or partial definition text.

A permissive post-processor that converted those into calls by supplying the original arguments would change the task: it would reconstruct the missing structured edit deterministically and collapse the experiment back toward target/index selection.

That would not be a valid rescue of E033.

## Interpretation

E033 fails the generation-validity gate for this compact generator and prompt surface.

The result is analogous to E022 in a narrower form: even one free-form call expression still introduces enough generation entropy that the decision layer cannot yet be cleanly evaluated through it.

Therefore:

- do **not** proceed to a full paired E033 baseline-vs-assisted run;
- do **not** tune a permissive parser against these 64 development examples;
- do **not** count deterministic reconstruction of omitted arguments as successful call generation.

A useful successor should retain deterministic verification while constraining the generated action more strongly, for example a narrow AST-operation schema that explicitly separates target selection from argument operations.

The existing index-selection evidence (E023/E025/E027/E031) remains unaffected.
