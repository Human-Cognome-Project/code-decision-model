# E015 — Same-class method-call supervision

Top-level function calls were useful for proving the pipeline, but they leave a large amount
of ordinary object-oriented code unused. Same-class method calls provide another source of
exact machine labels without requiring an LSP or another model.

E015 recognizes direct calls such as:

    self.parse(value)
    cls.from_value(value)
    Factory.from_value(value)

and masks only the target attribute before constructing the decision.

## Integrity controls

- only methods directly contained in a top-level class are considered;
- nested function, lambda, and nested-class bodies are not attributed to the caller;
- duplicate method names and property descriptors are excluded;
- the caller receiver is inferred from its first positional parameter rather than assuming `self`;
- candidates must share the target binding kind: instance, class, or static;
- candidates must share the target invocation shape after removing the implicit receiver;
- target identifier leakage in the rendered caller rejects the example;
- examples without the full hard candidate set are skipped.

The next step is a census on the existing benchmark repositories. If density is materially
higher than top-level function supervision, method decisions can be pooled as a second task
before attempting cross-file resolution.
