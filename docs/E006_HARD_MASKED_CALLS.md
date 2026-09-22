# E006 — Structurally controlled masked call recovery

The first masked-call benchmark on Click produced an encouraging-looking model score, but a
simple structural baseline explained it:

| Baseline | Test accuracy |
| --- | ---: |
| Random (16-way) | 6.25% |
| Lexical overlap | 10.8% |
| Raw UniXcoder cosine | 16.2% |
| Frozen UniXcoder + trained decision head | 30.3% mean |
| Same-file + call-arity heuristic | **32.4%** |

That means E005 is useful as a diagnostic, but it does not yet demonstrate semantic code
judgment.

E006 removes the two strongest structural shortcuts before the next model benchmark.

## Candidate controls

For every retained example, all candidates:

1. come from the **same source file** as the caller;
2. have the **same positional function arity** as the true target;
3. exclude the caller itself;
4. omit file paths from the scored candidate text;
5. use a fixed candidate count.

The caller still has the true target identifier replaced with `__CALL_TARGET__`.

If a call site cannot supply the full controlled candidate set, it is skipped rather than padded
with easier negatives.

## Why this is a better gate

A path-matching rule has no information because all candidates share the file.

An arity rule has no information because all candidates share the target's arity.

Exact callee-name matching is unavailable because the target is masked.

The remaining evidence is closer to what we actually care about: naming semantics, data flow,
result use, and candidate behavior.

The next census should measure how many 4-way and 8-way E006 examples real repositories can
supply before selecting the next benchmark corpus.
