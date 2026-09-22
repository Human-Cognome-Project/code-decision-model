# E018 — Hard environmental constraints

Unique priors should live outside the neural model as machine-checkable
constraints. E018 adds a minimal interface so deterministic validators can
veto or re-rank candidates after the discriminative scorer has produced logits.

## Design

```text
scores = decision_head(context, question, candidates)
result = apply_constraints(scores, context, question, candidates, constraints)
```

- Constraints are pure functions of the supplied strings.
- They never consult the neural model or any LLM.
- A candidate must pass *every* constraint to remain allowed.
- If nothing remains legal the result is marked `escalate` rather than forcing
  a choice.
- Surviving scores are renormalised with a masked softmax.

## Why this belongs here

The broader hypothesis is that a specialised (possibly non-frontier) model
expresses programmatic need, while a deterministic secondary layer completes
that need under hard predicates. The decision head already supplies ranking;
the missing piece is an explicit place for the predicates themselves.

Keeping constraints outside the model:

- prevents soft drift of unique priors back toward the median,
- makes every rejection auditable,
- lets the neural component stay small and open-weight,
- gives the surrounding system a clean escalate signal.

## Minimal built-ins

The first implementation ships three trivial constraints for tests and
examples:

- `RequireSubstring` — candidate must contain a literal
- `RejectSubstring` — candidate must not contain a literal
- `AllAllowed` — no-op baseline

Real project constraints (arity match, type-checker diagnostics, invariant
oracles, test outcomes, etc.) plug into the same `Constraint` protocol.

## Success signal

This experiment is successful when:

1. the interface stays small and dependency-free,
2. illegal candidates are reliably removed,
3. an empty surviving set produces `escalate=True`,
4. later experiments can attach stronger deterministic oracles without
   changing the decision head.
