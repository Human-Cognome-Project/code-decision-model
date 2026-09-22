# E004 — Cached frozen-encoder training

The intended code-decision architecture should not repeatedly run a large code encoder while
only a small decision head is being trained.

E004 adds a cached training path for frozen backbones.

## Invariant

For a frozen encoder:

~~~text
E(context)
E(question)
E(candidate)
~~~

are deterministic for the duration of head training. Recomputing them every epoch wastes the
majority of the work.

The experiment therefore:

1. deduplicates every unique context, question, and candidate string;
2. encodes each unique string once;
3. stores the detached representations;
4. trains only the decision scorer;
5. refuses to cache when any encoder parameter remains trainable.

The final guard is important. If the backbone were updated while its old representations were
still cached, the training objective would silently become inconsistent.

## Repository consequence

Repository symbol candidates repeat across many decisions, so caching is not merely an offline
training optimization. It is part of the intended runtime architecture:

~~~text
repository symbol -> stable code representation -> cache
                                      |
question/context -> representation -> decision head
~~~

A future repository index can invalidate embeddings only for symbols whose source actually
changes.

## Gate

Before using UniXcoder on a real repository, tests require:

- direct and cached logits to match;
- shared candidate strings to be encoded only once;
- cached head training to perform zero encoder calls;
- the cached path to overfit the same deterministic sanity task as E001.
