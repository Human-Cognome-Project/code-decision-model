# E033 — Call-expression intent

E022 asked a 0.5B generator for a whole repaired function and it produced no
valid repair in 24 attempts. E023 asked for a candidate index and the decision
layer's effect became measurable, then replicated (E025, E027). Between those
two lies the question this project ultimately cares about: can a compact
generator write **actual code** under hard guarantees?

E033 opens that question at the smallest possible step. The generator emits one
Python call expression, callee and arguments:

```text
normalize(prepared, strict=True)
self.clean(value)
```

Deterministic code splices it over the masked call in the caller's AST and the
E021 verifier compares the result, AST to AST, with the machine-labelled repair.
The generation surface is a few tokens, so the validity floor that stopped E022
should be reachable, while the output is real code rather than a pointer.

## Verification order

Every generated fragment passes through four deterministic checks, in this order,
and feedback names only the failing category:

| Check | Failure category | What it enforces |
| --- | --- | --- |
| parses as exactly one call expression | `invalid_call_expression` | output is code, not prose or a function |
| callee names exactly one candidate | `unknown_target` / `ambiguous_target` | the choice is drawn from the repository's real symbols and identifies a single definition |
| arguments bind the candidate's signature (E024) | `unbindable_call` | the call would not raise `TypeError` against the real definition |
| spliced caller equals the expected repair | `wrong_target` / `wrong_arguments` | the right callee, and the original call site's arguments preserved |

The third check is the one that makes this "code generation controlled by
predicates": a call that names the right candidate with arguments that cannot
bind is rejected before any truth comparison, on the strength of the AST alone.
`wrong_arguments` is reported only when the callee is right, so the two failure
modes E022 conflated (wrong choice vs malformed edit) are separable.

Callee resolution never consults the label. Repository-wide pools (E030) do not
guarantee unique symbol names, so a call whose callee matches several candidates
is rejected as `ambiguous_target` rather than credited to whichever duplicate is
correct. A task whose answer symbol is duplicated in its own pool is therefore
unwinnable under this protocol; the census reports how many such tasks exist.

## Task scope

- Tasks: the three hard masked-call families (E006, E015, E030).
- Eligibility: exactly one masked call site in the caller. Callers that invoke
  the masked target twice would need one intent per site and are excluded.
- Candidates and labels are unchanged; the answer is still the machine-labelled
  target, and the expected repair is E021's.

`python examples/census_call_intent.py` reports eligibility per task family and
the argument-count distribution at the masked call, which sets how much the
generator has to reproduce beyond the callee name.

## Harness

`run_call_intent_loop` and `run_paired_call_intent` mirror E021/E023: bounded
attempts, category-only feedback, a fallible recommendation in the assisted arm
only, fresh generator per arm. Outcomes carry the same properties as the other
harnesses, so E026 statistics apply unchanged. A test confirms that for every
eligible decision on this repository, the expected repair itself is accepted as
a valid intent.

## What this tests, per the contribution rule

1. **Open question**: can the frozen compact generator emit a single correct
   call expression, and does the decision recommendation reduce corrective
   burden when the output is code rather than an index?
2. **Deterministic signal**: the four-stage verifier above; the E021 expected
   repair as ground truth; E024 bindability as a hard predicate on the fragment.
3. **Comparison**: E027 on the same tasks under the index protocol (ceiling for
   decision effect), E022 (floor for validity). First-pass parse validity and
   `unbindable_call` rate are reported separately from success.
4. **Stop condition**: if the generator's first-pass validity (parse plus
   bindable) is below the E022 floor's neighbourhood, i.e. it cannot reliably
   emit one well-formed call, the code-fragment direction stops at index-level
   edits and larger structured intents are not attempted. If validity is
   reachable but the recommendation no longer reduces burden, the decision
   layer's benefit is specific to selection and that is recorded as such.

## Predictions

- Validity: single-expression output should clear the floor. E022's failures
  were `invalid_python` and `placeholder_remaining` on whole functions; neither
  has an analogue when the output is one expression and the placeholder is
  spliced deterministically.
- Recommendation effect: if the generator follows recommendations as in E028,
  the callee will be right whenever the recommendation is, and the residual
  failure will be `wrong_arguments`. That would locate the generator's actual
  limitation for the first time, independent of decision quality.
- Predicate value: `unbindable_call` should catch a share of wrong-callee
  attempts before the truth comparison, larger on E030 cross-file pools.

## Out of scope

E031 remains the frozen replication gate and excludes this. E029/E032 rejection
memory can be composed with this loop later; the first live run should measure
the plain loop so the generation effect is not confounded with memory.
