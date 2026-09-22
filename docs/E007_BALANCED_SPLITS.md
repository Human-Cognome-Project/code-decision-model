# E007 — Balanced source-group evaluation splits

Hashing every source file independently is deterministic, but on small and medium repositories
it can produce empty or tiny validation/test partitions by chance.

E007 adds a second splitter intended for experiments.

## Requirements

The balanced splitter:

- keeps every source file entirely within one partition;
- targets example counts rather than file counts;
- guarantees every requested partition receives at least one source group;
- is deterministic for a seed;
- processes larger source groups first so a large file cannot become a late balancing surprise;
- supports repository namespacing before pooling multiple repositories.

The algorithm does **not** split a source file to improve numerical balance. Source isolation wins
over exact percentages.

For pooled experiments, namespace provenance first:

~~~python
pooled = [
    *namespace_repository_examples(click_examples, "click"),
    *namespace_repository_examples(pydantic_examples, "pydantic"),
]
dataset = split_repository_examples_balanced(
    pooled,
    train_fraction=0.70,
    validation_fraction=0.15,
)
~~~

This keeps paths such as `tests/test_main.py` from two repositories from being mistaken for the
same source group.
