# E012 — Source-clustered evaluation uncertainty

Examples from the same source file are not independent. They share local naming conventions,
style, candidate pools, and implementation context.

Reporting ordinary binomial confidence intervals would therefore make small benchmarks look
more certain than they are.

E012 adds:

- exact micro accuracy;
- per-repository accuracy from namespaced provenance;
- repository-macro accuracy;
- percentile bootstrap intervals that resample whole source files;
- repository-macro bootstrap intervals that resample source files independently inside each
  repository before macro-averaging.

The bootstrap is deterministic for a seed and has no dependency beyond the Python standard
library.

Future benchmark summaries should report both micro accuracy and repository-macro accuracy with
source-clustered intervals whenever the evaluation spans multiple repositories.
