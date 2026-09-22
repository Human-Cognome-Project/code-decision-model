# Experiments

## E001 — Can the separated-candidate primitive learn at all?

Before downloading or fine-tuning a pretrained code model, the smallest version should
demonstrate that gradients can teach the architecture a machine-verifiable code decision.

### Task

Python ASTs provide exact local call edges. For each top-level function that calls exactly
one other top-level function, construct:

- context: the caller source;
- question: which candidate function is directly called?;
- candidates: all top-level function signatures in the module;
- target: the callee identified by the AST.

No LLM labels are involved.

### Model

The E001 model intentionally uses the toy hashed-token encoder. Candidate representations are
still independent and cacheable.

### Pass condition

The model must reliably overfit a tiny deterministic set. Failure means the decision path or
training implementation is broken and there is no reason to try a larger encoder.

Passing E001 is **not** evidence that the architecture generalizes. The next useful experiment is
held-out generalization with a pretrained code encoder and larger machine-generated datasets.

Run:

```bash
python examples/learn_ast_calls.py
```

## E019 — Hard environmental constraints

See [E019_HARD_CONSTRAINTS.md](E019_HARD_CONSTRAINTS.md).

Adds a minimal interface so deterministic validators can veto or filter
candidates after neural scoring. Unique priors stay outside the model as
machine-checkable constraints; an empty surviving set produces an explicit
escalate signal.

## E021 — Corrective-turn repair harness

See [E021_CORRECTIVE_TURN_HARNESS.md](E021_CORRECTIVE_TURN_HARNESS.md).

Measures deterministic masked-call repair as a bounded baseline-vs-assisted
correction loop.

Companion example:
[E021_CORRECTIVE_TURN_MOCK.md](E021_CORRECTIVE_TURN_MOCK.md) exercises the
paired measurement path with deterministic mock generators and no model download.

## E022 — Open generator on the corrective-turn harness

See [E022_OPEN_GENERATOR_REPAIR.md](E022_OPEN_GENERATOR_REPAIR.md).

First live open-generator experiment on the E021 harness. Reserved for a pinned
real model; the mock path lives under E021.


### E022 live result

See [E022_LIVE_QWEN_RESULT.md](E022_LIVE_QWEN_RESULT.md).

The first pinned Qwen 0.5B pilot produced zero verified repairs in either arm.
The result is inconclusive for correction-turn reduction because the generator
did not cross the deterministic validity floor.
