# E031 — Development-independent replication preregistration

E027 showed that the structured-selection corrective-burden effect survives
leave-one-repository-out scorer training across four development repositories.
Those repositories were nevertheless visible while the architecture, encoder,
scorer shape, prompt, and protocol were developed.

E031 is the primary development-independent replication gate.

This document freezes the repository candidate pool, eligibility rule, protocol,
primary metric, and statistics **before extraction counts, scorer results, or
generator outcomes are observed on the new repositories**.

## Frozen candidate pool

The pool order below is fixed. Each repository is pinned to the default-branch
commit observed when this preregistration was written.

| Order | Repository | Branch | Pinned commit |
| ---: | --- | --- | --- |
| 1 | google-deepmind/alphafold | main | `c77e5d2a8961d1a353632c462914ff0a32a950f6` |
| 2 | pyodide/pyodide | main | `e4d3ae954d01d61a3e90531d63b881f2d33361b4` |
| 3 | optuna/optuna | master | `7d08bfa1824606d7caedb80abfd8558bc63826d7` |
| 4 | pytest-dev/pytest | main | `6a9ba0f02f827a54cff6ab4da0dddecd65444ff6` |
| 5 | google/yapf | main | `12005095296072751e3e4c1f33a047d41b0ce18d` |
| 6 | DLR-RM/stable-baselines3 | master | `7cfb4dd6055e74b5caa4ed4d6777492209946e26` |
| 7 | redis/redis-py | master | `2fdaaa32b5fcf767dfa557c86e7d050567597e3f` |
| 8 | getpelican/pelican | main | `3c69dc68d25a761911697467c765a16e68915c74` |

None of these repositories is one of the four E027 development repositories.

## Extraction-only eligibility

Before any scorer is trained or generator is run, apply the frozen E027
extractors to every candidate repository:

- `repository_hard_masked_call_examples`;
- `repository_hard_masked_method_call_examples`;
- candidate count: 4;
- candidate body characters: 512;
- extraction seed: 0.

A repository is eligible when it yields:

1. at least **25 total examples** across the two frozen task types; and
2. examples from at least **5 distinct source files**.

Select the **first four eligible repositories in the frozen pool order**.

The eligibility rule may inspect only extraction counts and source provenance,
not encoder scores, scorer accuracy, generator behavior, or end-to-end outcomes.

If fewer than four repositories qualify, do **not** lower the threshold. Append a
new pinned candidate pool in a preregistration amendment before any model scoring
is performed on newly added candidates.

Once the four repositories are selected, record their extraction counts in this
experiment series before running the primary model experiment.

## Frozen E027 protocol

E031 intentionally excludes later exploratory changes. In particular, E029
rejection memory and E030 cross-file supervision are **not** part of the primary
replication.

Use the E027 protocol unchanged:

- task families:
  - `python.hard_masked_direct_call`;
  - `python.hard_masked_same_class_call`;
- context focus: `focus_hard_call_context(..., radius_lines=0)`;
- encoder: `nomic-ai/CodeRankEmbed`;
- encoder max length: 512;
- normalized embeddings: false;
- scorer: `PairwiseMLPScorer(hidden=32)`;
- scorer seed: 2;
- optimizer: AdamW;
- learning rate: 1e-3;
- weight decay: 1e-2;
- one scorer-training epoch;
- training order seed: 20001;
- batch size: 32;
- gradient clipping: 1.0;
- generator: `Qwen/Qwen2.5-Coder-0.5B-Instruct`;
- generator revision:
  `ea3f2471cf1b1f0db85067f1ef93848e38e88c25`;
- greedy decoding;
- maximum new tokens: 8;
- exact E027 structured-choice prompt/parser;
- maximum two attempts per arm;
- category-only deterministic verifier feedback.

No hyperparameter, prompt, parser, threshold, attempt-budget, or task-definition
change is permitted after extraction counts are seen.

## Evaluation design

Run leave-one-repository-out rotation across the four selected E031 repositories.

For each fold:

- the held-out repository contributes only test examples;
- all examples from the other three repositories train the scorer;
- there is no validation-selection step;
- the generator settings are identical in baseline and assisted arms;
- the assisted arm receives the scorer's fallible recommendation exactly as E027.

Each task is therefore evaluated once by a scorer that has never trained on its
repository.

## Primary endpoint

The primary endpoint is **success within two attempts**.

Report:

- baseline successes / tasks;
- assisted successes / tasks;
- paired assisted-minus-baseline success-rate delta.

The replication supports the E027 effect if the direction is positive under the
frozen protocol. Statistical uncertainty is reported rather than converted into
a new tuning rule.

## Predeclared statistics

Use the E026 paired analysis unchanged:

- exact two-sided McNemar test on discordant task outcomes;
- source-file clustered bootstrap;
- bootstrap resampling within held-out-repository strata;
- 5,000 bootstrap replicates;
- report the 95% interval for the pooled success-rate delta.

Secondary descriptive measures:

- first-pass success;
- terminal failures;
- mean attempts within budget;
- decision accuracy, micro and repository-macro;
- correction-turn delta among paired successes;
- per-repository folds.

Small individual folds remain descriptive.

## Stop / interpretation rules

Do not:

- replace a selected repository because its model result is inconvenient;
- retune on this set;
- add E029 rejection memory to rescue a weak primary result;
- add E030 cross-file examples to increase task count;
- swap generator or encoder before recording the primary E031 result.

If the frozen replication is weak, null, or negative, record that result before
starting any explanatory follow-up.

Exploratory work may continue in parallel, but E031 remains a clean test of the
already-frozen E027 claim.
