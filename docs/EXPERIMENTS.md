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

## E022 — Open generator on the corrective-turn harness

See [E022_OPEN_GENERATOR_REPAIR.md](E022_OPEN_GENERATOR_REPAIR.md).

Attaches a generator (mock first, real open model next) to the E021 repair
harness and measures paired correction turns with vs without a fallible
decision recommendation.
