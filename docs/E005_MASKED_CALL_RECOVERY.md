# E005 — Masked call recovery

The direct-call dataset is useful for testing the pipeline, but it is not a meaningful
capability benchmark: the caller source literally contains the callee identifier.

E005 removes that shortcut while keeping machine-verifiable labels.

## Construction

For each caller with exactly one distinct top-level same-file call target:

1. derive the target from the Python AST;
2. deep-copy the caller AST;
3. replace every executable `Name` reference to the target with `__CALL_TARGET__`;
4. unparse the masked caller;
5. present repository-wide candidate definitions containing source path, signature, and a
   bounded implementation excerpt;
6. ask which candidate definition should replace the masked target.

The target label is unchanged and still comes from the parser, not from another model.

## Why this is harder

Direct-call recovery can be solved by finding the same identifier in the context and candidate
list. Masked recovery cannot use that equality. Useful evidence instead includes:

- argument shape;
- surrounding data flow;
- how the result is consumed;
- caller and candidate naming semantics;
- candidate implementation behavior;
- nearby control flow.

It is still not a full code-reasoning benchmark. Naming conventions can provide strong clues,
and same-file functions share local style. Those are legitimate baselines to measure rather
than hide.

## First benchmark

The first real model experiment should compare at least:

- random choice;
- a lexical/text-similarity baseline;
- frozen UniXcoder + trained decision head;
- the toy hashed encoder + the same decision head.

Train/validation/test must remain source-file disjoint using the E003 splitter.

A positive result here would justify moving to stronger supervision such as cross-file LSP
resolution, compiler diagnostics, and patch/test outcomes.
