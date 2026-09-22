# E023 — Call-site bindability predicate

E019 added the hard-constraint interface but shipped only substring placeholders.
E023 adds the first constraint derived from real machine-checkable facts and
measures what it removes from the decision problem.

## Predicate

A candidate definition is legal only if Python's argument-binding rules could
bind every masked call site in the caller:

```text
shapes    = call sites of __CALL_TARGET__ in the caller AST
params    = parameters of the candidate definition
allowed_i = all(binds(params_i, shape) for shape in shapes)
```

`binds` follows CPython's rules: positional capacity, positional-only parameters
refusing keywords, unknown keywords without `**kwargs`, duplicate values, and
required parameters that nothing supplies.

## Soundness before completeness

A hard predicate that vetoes the true target is worse than no predicate: it
converts a recoverable ranking error into a forced escalation. Every unknown is
therefore resolved in the candidate's favour:

- `*args` at the call site makes the positional count a lower bound only;
- `**kwargs` at the call site may supply any keyword-bindable parameter;
- unreadable candidate signatures, unparseable callers, and absent call sites
  leave every candidate allowed;
- when a candidate body is truncated before its header, defaults are unknown and
  every parameter is treated as optional;
- an attribute call (`self.__CALL_TARGET__(...)`) is accepted under either the
  bound-method reading or the static reading.

The census script asserts soundness on machine-labelled corpora: the target must
never be vetoed. The test suite repeats this over this repository's own source.

## Census on this repository

`python examples/census_call_site_predicate.py`

| Corpus | Examples | Any veto | Mean survivors | Uniform | Predicate + uniform | Truth vetoed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E005 masked direct call, 16 repository-wide candidates | 83 | 94.0% | 7.11 | 6.2% | 28.5% | 0 |
| E006 hard masked direct call, 4 shape-controlled | 49 | 2.0% | 3.98 | 25.0% | 25.2% | 0 |
| E015 hard masked same-class call, 4 shape-controlled | 4 | 0.0% | 4.00 | 25.0% | 25.0% | 0 |

Two readings:

1. On realistic candidate pools the predicate alone removes most of the
   decision. The neural scorer should be measured on what survives the
   predicate, and a "predicate + uniform" baseline replaces raw random chance.
2. On the hardened corpora the predicate is almost a no-op, as intended: E006
   and E015 already control call shape. The single E006 veto comes from a
   keyword name the shape control does not see, which is a legitimate binding
   failure rather than a shortcut.

This is a census, not a model result. Counts are small and come from one
repository.

## Why this matters for the practical criterion

The project's stated end state is a small generator whose choices are held to
hard predicate requirements. This is the first predicate that expresses a
requirement of the surrounding code rather than a literal string. It plugs into
`apply_constraints` unchanged, so the decision head is untouched and every veto
is auditable.

## Next

- Attach the predicate to the E021 repair loop as a pre-generation filter and
  measure whether hard (non-fallible) veto evidence changes correction turns
  separately from the fallible neural recommendation.
- Add the next predicate on the supervision ladder: type-checker diagnostics on
  the repaired caller.
