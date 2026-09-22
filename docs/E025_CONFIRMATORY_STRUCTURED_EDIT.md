# E025 — Full held-out structured-edit confirmation

E023 produced the first positive corrective-burden signal on a 12-example pilot.
E025 repeats the same structured-edit protocol over the full 63-example held-out
test split without changing the generator, decision intervention, decoding, or
attempt budget.

## Fixed setup

Generator:

- model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- revision: `ea3f2471cf1b1f0db85067f1ef93848e38e88c25`
- greedy decoding
- `max_new_tokens=8`
- maximum two attempts per arm
- strict full-response candidate parser

Decision intervention:

- encoder: `nomic-ai/CodeRankEmbed`
- scorer: `PairwiseMLPScorer(hidden=32)`
- seed: 2
- one training epoch
- held-out decision accuracy: 38/63 (60.3%)

Corpus:

- 400 total examples
- 277 train
- 60 validation
- 63 held-out test
- 32 browser-use
- 24 crawl4ai
- 4 markitdown
- 3 scrapling
- 9 function-call tasks
- 54 same-class method-call tasks

The split is held out by source grouping within the same repositories. This is not
an unseen-repository experiment.

## Primary result

| Metric | Baseline | Assisted |
| --- | ---: | ---: |
| First-pass success | 15/63 (23.8%) | 38/63 (60.3%) |
| Success within two attempts | 32/63 (50.8%) | 44/63 (69.8%) |
| Terminal failures | 31/63 | 19/63 |
| Mean attempts, all tasks | 1.76 | 1.40 |

Paired outcomes:

- both succeed: 23
- assisted only: 21
- baseline only: 9
- neither succeeds: 10

The success-rate delta is **+19.0 percentage points** in favour of the assisted
condition.

Exact McNemar on the 30 discordant tasks:

- assisted only: 21
- baseline only: 9
- two-sided exact p = 0.0428

## Source-file-clustered uncertainty

A 5,000-replicate percentile bootstrap resampled source files within repository
strata so repository composition was preserved.

95% intervals:

- success-rate delta: **+2.7 to +32.8 percentage points**
- first-pass success-rate delta: **+20.9 to +50.9 percentage points**

Both intervals exclude zero on this held-out split.

## Correction turns among paired successes

Among the 23 tasks solved by both arms:

- assisted used fewer correction turns on 9
- the same number on 14
- more on 0
- mean baseline-minus-assisted correction delta: **+0.39 turns**

An exact sign test over the 9 unequal paired-success deltas gives a two-sided
p-value of **0.0039**.

This conditional metric remains secondary to success within budget because the
intervention changes which tasks enter the paired-success subset.

## Structured-output validity

Neither condition produced an invalid candidate-format attempt.

That matters because E022 failed before the decision-layer question could be
measured: full-function generation never crossed the deterministic validity
floor. E025 shows that once syntax generation is removed from the path, the
decision intervention can be evaluated directly.

## Repository and task breakdowns

The direction of the aggregate success effect was non-negative in every repository,
but repository sample sizes are highly uneven:

- browser-use: +9.4 percentage points (32 tasks)
- crawl4ai: +29.2 points (24 tasks)
- markitdown: 0 points (4 tasks)
- scrapling: +66.7 points (3 tasks)

By task type:

- functions: +22.2 points (9 tasks)
- methods: +18.5 points (54 tasks)

These subgroup values are descriptive only. The small function, markitdown, and
scrapling samples are not adequate for separate claims.

## Interpretation

E025 confirms the E023 pilot on the project's current held-out test split.

The result supports the narrower claim that, when a compact generator is asked
to make a structured code decision rather than regenerate the whole function,
fallible repository decision evidence can reduce corrective burden under a fixed
generation budget.

The result does **not** yet establish unseen-repository generalization, broader
code-repair performance, or benefit when arbitrary free-form patches must be
generated.

## Next gate

Do not tune further on these 63 examples.

The next experiment should hold out entire repositories, or use a second pinned
repository set not used for scorer development, while preserving:

- the same Qwen revision;
- the same structured-output protocol;
- the same two-attempt budget;
- the same deterministic supervision;
- predeclared paired statistics from E026.

A successful unseen-repository replication would materially strengthen the
architecture claim. A failure would identify repository-specific transfer as the
next limiting factor.
