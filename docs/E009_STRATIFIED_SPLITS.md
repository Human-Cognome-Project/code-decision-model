# E009 — Repository-stratified evaluation splits

A globally balanced pooled split can still create a misleading benchmark: one large repository
may dominate the test partition while another appears only in training.

E009 balances source-file groups **inside each repository namespace** and then combines the
partitions.

For repositories with enough source files, this guarantees representation in train, validation,
and test while preserving source-file isolation.

Small repositories that cannot populate all requested partitions have an explicit policy:

- `small_namespace="train"`: use them only as additional training data;
- `small_namespace="error"`: reject the split.

This makes per-repository held-out reporting meaningful and prevents a pooled aggregate from
silently becoming a single-repository result.
