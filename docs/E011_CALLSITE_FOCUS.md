# E011 — Call-site-focused context

Some callers are much longer than the encoder context window, and global mean pooling can dilute
the few lines that establish what the missing call is doing.

E011 adds a model-independent context transform that keeps:

- decorators and the outer function definition header;
- a configurable number of lines before the first masked call;
- all lines spanning multiple masked-call occurrences;
- a configurable number of lines after the last masked call.

Omitted regions are represented by neutral comment markers. Candidates and labels are unchanged.

This addresses two separate questions:

1. Does the encoder actually see the masked call site?
2. Does concentrating the representation around the use site improve discrimination?

Because it is a preprocessing transform, it can be applied consistently to UniXcoder and any
later compact encoder comparison.


## Compact-header mode

For pathological signatures or decorators, the complete function prefix can itself exceed a
bounded encoder window. Setting `compact_header=True` replaces decorators and the complete
signature with only:

    def function_name(...):

or its async equivalent.

This preserves the caller identity and async status while guaranteeing that annotations,
defaults, decorators, and long signatures cannot push the call site out of view. The compact
mode is evaluated separately because those removed details may themselves carry useful evidence.
