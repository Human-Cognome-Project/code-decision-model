# E008 — Supervision integrity hardening

The decision model is only as trustworthy as the machine-generated labels used to train and
evaluate it. E008 closes three subtle shortcuts/errors before treating larger benchmark results
as evidence.

## Nested scopes

A raw `ast.walk(function)` enters nested functions, lambdas, and classes. That can incorrectly
attribute an inner call to its enclosing function.

Direct-call extraction now walks the caller body while refusing to enter nested execution
scopes. A function with only a call inside a nested function therefore produces no outer call
edge.

## Exact-name leakage

Replacing executable `Name` nodes is not enough. The target identifier can survive inside a
string literal, annotation, nested definition name, or attribute and restore an easy text match.

After masking, an example is discarded if the exact target identifier still appears anywhere in
the rendered caller text.

## Structural call shape

Hard negatives now match the target on AST-derived:

- total positional parameters;
- required positional parameters;
- total keyword-only parameters;
- required keyword-only parameters;
- presence of `*args`;
- presence of `**kwargs`;
- async vs synchronous definition.

This is deliberately stricter than ordinary call compatibility. The goal is to remove cheap
structural clues before asking whether the representation contains useful semantic evidence.
